#!/usr/bin/env bash
#
# OpenClaw Team Agent Spawner
# Usage: ./spawn-agent.sh <agent-type> <task-description>
#

set -e

AGENT_TYPE=$1
TASK_DESC=$2
WORKSPACE="${HOME}/clawd"

if [ -z "$AGENT_TYPE" ] || [ -z "$TASK_DESC" ]; then
    echo "Usage: ./spawn-agent.sh <planning|coding|review> <task-description>"
    echo ""
    echo "Examples:"
    echo "  ./spawn-agent.sh planning 'Analyze new feature requirements'"
    echo "  ./spawn-agent.sh coding 'Implement user authentication'"
    echo "  ./spawn-agent.sh review 'Review PR #123'"
    exit 1
fi

# Validate agent type
if [[ ! "$AGENT_TYPE" =~ ^(planning|coding|review)$ ]]; then
    echo "Error: Invalid agent type. Use: planning, coding, or review"
    exit 1
fi

echo "🚀 Spawning ${AGENT_TYPE} agent..."
echo "   Task: ${TASK_DESC}"
echo ""

# Build agent-specific configuration
case $AGENT_TYPE in
    planning)
        AGENT_FILE="${WORKSPACE}/agents/planning-agent.md"
        MODEL="anthropic/claude-opus-4-5"
        LABEL="planning-$(date +%s)"
        ;;
    coding)
        AGENT_FILE="${WORKSPACE}/agents/coding-agent.md"
        MODEL="kimi-code/kimi-for-coding"
        LABEL="coding-$(date +%s)"
        ;;
    review)
        AGENT_FILE="${WORKSPACE}/agents/review-agent.md"
        MODEL="anthropic/claude-sonnet-4-5"
        LABEL="review-$(date +%s)"
        ;;
esac

echo "📋 Agent Config: ${AGENT_FILE}"
echo "🤖 Model: ${MODEL}"
echo "🏷️  Label: ${LABEL}"
echo ""

# Create the task with agent context
TASK="
## Agent Task

**Role:** ${AGENT_TYPE} Agent
**Task:** ${TASK_DESC}

### Context
Read your agent configuration at: ${AGENT_FILE}
Follow the Sengdao2 patterns defined there.

### Deliverables
1. Complete the assigned task
2. Save progress to memory/planning/, memory/coding/, or memory/review/
3. Report back to main session with:
   - Status (done/blocked)
   - Output location
   - Any issues encountered

### Checkpoint
Report progress every 10 minutes.
Save work immediately after completing sub-tasks.

### Task Details
${TASK_DESC}
"

echo "📤 Sending task to agent..."
echo ""

# Use openclaw sessions spawn (if available)
# Fallback: echo instructions
if command -v openclaw &> /dev/null; then
    openclaw sessions spawn \
        --agent-id "${AGENT_TYPE}" \
        --model "${MODEL}" \
        --label "${LABEL}" \
        --task "${TASK}"
else
    echo "⚠️  openclaw CLI not found. Manual instructions:"
    echo ""
    echo "1. Open new terminal/session"
    echo "2. Set agent context from: ${AGENT_FILE}"
    echo "3. Execute task: ${TASK_DESC}"
    echo "4. Report back to main session"
fi

echo ""
echo "✅ Agent spawn request complete"
echo "📊 Monitor with: sessions_list"
