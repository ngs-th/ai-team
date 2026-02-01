#!/bin/bash
#
# 🤖 AI Team Monitor Script
# Monitors agent heartbeats, deadlines, and generates reports
#

set -e

# Configuration
MEMORY_DIR="${HOME}/clawd/memory/team"
ALERT_THRESHOLD_MINUTES=30
DATE_FORMAT="+%Y-%m-%d %H:%M:%S"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure directory exists
mkdir -p "$MEMORY_DIR"

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }

get_current_timestamp() { date +%s; }
format_timestamp() { date -r "$1" "$DATE_FORMAT" 2>/dev/null || date -d "@$1" "$DATE_FORMAT"; }

# Check if jq is available
if ! command -v jq &> /dev/null; then
    log_error "jq is required but not installed. Install with: brew install jq"
    exit 1
fi

# ====================
# Heartbeat Check
# ====================
check_heartbeats() {
    log_info "Checking agent heartbeats..."
    
    local agent_status_file="$MEMORY_DIR/agent-status.json"
    local current_time=$(get_current_timestamp)
    local alert_threshold=$((ALERT_THRESHOLD_MINUTES * 60))
    local silent_agents=()
    
    if [[ ! -f "$agent_status_file" ]]; then
        log_warn "Agent status file not found: $agent_status_file"
        return 1
    fi
    
    # Check each agent
    while IFS= read -r agent; do
        local agent_id=$(echo "$agent" | jq -r '.id')
        local agent_name=$(echo "$agent" | jq -r '.name')
        local last_heartbeat=$(echo "$agent" | jq -r '.last_heartbeat // empty')
        local status=$(echo "$agent" | jq -r '.status')
        
        if [[ "$status" == "active" && -n "$last_heartbeat" ]]; then
            local heartbeat_ts=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${last_heartbeat%%+*}" +%s 2>/dev/null || \
                                date -d "$last_heartbeat" +%s 2>/dev/null || \
                                echo "0")
            local time_diff=$((current_time - heartbeat_ts))
            
            if [[ $time_diff -gt $alert_threshold ]]; then
                local minutes=$((time_diff / 60))
                silent_agents+=("⚠️ $agent_name ($agent_id): Silent for ${minutes}m")
            fi
        fi
    done < <(jq -c '.agents[]' "$agent_status_file" 2>/dev/null || echo "")
    
    if [[ ${#silent_agents[@]} -eq 0 ]]; then
        log_success "All active agents reporting normally"
        return 0
    else
        log_warn "Found ${#silent_agents[@]} silent agent(s):"
        for alert in "${silent_agents[@]}"; do
            echo "  $alert"
        done
        return 1
    fi
}

# ====================
# Deadline Check
# ====================
check_deadlines() {
    log_info "Checking task deadlines..."
    
    local tasks_file="$MEMORY_DIR/active-tasks.json"
    local current_time=$(get_current_timestamp)
    local overdue_tasks=()
    
    if [[ ! -f "$tasks_file" ]]; then
        log_warn "Tasks file not found: $tasks_file"
        return 1
    fi
    
    while IFS= read -r task; do
        local task_id=$(echo "$task" | jq -r '.id')
        local task_title=$(echo "$task" | jq -r '.title')
        local eta=$(echo "$task" | jq -r '.eta // empty')
        local status=$(echo "$task" | jq -r '.status')
        local assignee=$(echo "$task" | jq -r '.assignee')
        
        if [[ "$status" == "in_progress" && -n "$eta" ]]; then
            local eta_ts=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${eta%%+*}" +%s 2>/dev/null || \
                          date -d "$eta" +%s 2>/dev/null || \
                          echo "0")
            
            if [[ $current_time -gt $eta_ts ]]; then
                local overdue_min=$(((current_time - eta_ts) / 60))
                overdue_tasks+=("⏰ $task_id: $task_title ($assignee) - Overdue by ${overdue_min}m")
            fi
        fi
    done < <(jq -c '.tasks[]' "$tasks_file" 2>/dev/null || echo "")
    
    if [[ ${#overdue_tasks[@]} -eq 0 ]]; then
        log_success "All tasks on track"
        return 0
    else
        log_warn "Found ${#overdue_tasks[@]} overdue task(s):"
        for task in "${overdue_tasks[@]}"; do
            echo "  $task"
        done
        return 1
    fi
}

# ====================
# Blocked Tasks Check
# ====================
check_blocked() {
    log_info "Checking blocked tasks..."
    
    local tasks_file="$MEMORY_DIR/active-tasks.json"
    local blocked_tasks=()
    
    if [[ ! -f "$tasks_file" ]]; then
        log_warn "Tasks file not found: $tasks_file"
        return 1
    fi
    
    while IFS= read -r task; do
        local task_id=$(echo "$task" | jq -r '.id')
        local task_title=$(echo "$task" | jq -r '.title')
        local status=$(echo "$task" | jq -r '.status')
        local blocked_by=$(echo "$task" | jq -r '.blocked_by // empty')
        local assignee=$(echo "$task" | jq -r '.assignee')
        
        if [[ "$status" == "blocked" || -n "$blocked_by" ]]; then
            blocked_tasks+=("🚧 $task_id: $task_title ($assignee) - Blocked by: $blocked_by")
        fi
    done < <(jq -c '.tasks[]' "$tasks_file" 2>/dev/null || echo "")
    
    if [[ ${#blocked_tasks[@]} -eq 0 ]]; then
        log_success "No blocked tasks"
        return 0
    else
        log_warn "Found ${#blocked_tasks[@]} blocked task(s):"
        for task in "${blocked_tasks[@]}"; do
            echo "  $task"
        done
        return 1
    fi
}

# ====================
# Generate Reports
# ====================
generate_hourly_report() {
    log_info "Generating hourly report..."
    
    local tasks_file="$MEMORY_DIR/active-tasks.json"
    local agent_file="$MEMORY_DIR/agent-status.json"
    
    local total_tasks=$(jq '.tasks | length' "$tasks_file" 2>/dev/null || echo "0")
    local in_progress=$(jq '[.tasks[] | select(.status == "in_progress")] | length' "$tasks_file" 2>/dev/null || echo "0")
    local done=$(jq '[.tasks[] | select(.status == "done")] | length' "$tasks_file" 2>/dev/null || echo "0")
    local blocked=$(jq '[.tasks[] | select(.status == "blocked")] | length' "$tasks_file" 2>/dev/null || echo "0")
    
    local active_agents=$(jq '[.agents[] | select(.status == "active")] | length' "$agent_file" 2>/dev/null || echo "0")
    local idle_agents=$(jq '[.agents[] | select(.status == "idle")] | length' "$agent_file" 2>/dev/null || echo "0")
    
    cat << EOF

📊 **AI Team Hourly Report**
$(date "$DATE_FORMAT")

**Tasks:**
• Total: $total_tasks | In Progress: $in_progress | Done: $done | Blocked: $blocked

**Agents:**
• Active: $active_agents | Idle: $idle_agents

$(if [[ $blocked -gt 0 ]]; then echo "⚠️ Attention: $blocked blocked task(s) need help"; fi)

EOF
}

generate_daily_report() {
    log_info "Generating daily report..."
    
    local tasks_file="$MEMORY_DIR/active-tasks.json"
    local agent_file="$MEMORY_DIR/agent-status.json"
    
    local total_tasks=$(jq '.tasks | length' "$tasks_file" 2>/dev/null || echo "0")
    local completed_today=$(jq '[.tasks[] | select(.status == "done" and .completed_at | startswith("'$(date +%Y-%m-%d)'"))] | length' "$tasks_file" 2>/dev/null || echo "0")
    local blocked=$(jq '[.tasks[] | select(.status == "blocked")] | length' "$tasks_file" 2>/dev/null || echo "0")
    
    cat << EOF

📊 **AI Team Daily Summary**
$(date "$DATE_FORMAT")

**Today's Progress:**
• Tasks Completed: $completed_today
• Tasks In Progress: $(jq '[.tasks[] | select(.status == "in_progress")] | length' "$tasks_file" 2>/dev/null || echo "0")
• Blocked Tasks: $blocked

**Active Agents:**
$(jq -r '.agents[] | select(.status == "active") | "• " + .name + ": " + .current_task' "$agent_file" 2>/dev/null || echo "None")

$(if [[ $blocked -gt 0 ]]; then echo "🚧 **Blocked Tasks Need Attention:**"; jq -r '.tasks[] | select(.status == "blocked") | "• " + .id + ": " + .title' "$tasks_file" 2>/dev/null; fi)

**Summary:** $(if [[ $blocked -eq 0 && $completed_today -gt 0 ]]; then echo "✅ Good progress today!"; elif [[ $blocked -gt 0 ]]; then echo "⚠️ Need to unblock tasks"; else echo "📋 Steady progress"; fi)

EOF
}

# ====================
# Telegram Output
# ====================
output_for_telegram() {
    # Strip colors for Telegram
    "$@" | sed 's/\x1b\[[0-9;]*m//g'
}

# ====================
# Main
# ====================
main() {
    local command="${1:-help}"
    
    case "$command" in
        heartbeat)
            check_heartbeats
            ;;
        deadlines)
            check_deadlines
            ;;
        blocked)
            check_blocked
            ;;
        hourly)
            generate_hourly_report
            ;;
        daily)
            generate_daily_report
            ;;
        all)
            check_heartbeats
            check_deadlines
            check_blocked
            ;;
        telegram-hourly)
            output_for_telegram generate_hourly_report
            ;;
        telegram-daily)
            output_for_telegram generate_daily_report
            ;;
        *)
            cat << EOF
🤖 AI Team Monitor

Usage: $0 <command>

Commands:
  heartbeat       Check agent heartbeats (>30 min = alert)
  deadlines       Check for overdue tasks
  blocked         List blocked tasks
  hourly          Generate hourly status report
  daily           Generate daily summary report
  all             Run all checks
  telegram-hourly Generate hourly report (plain text)
  telegram-daily  Generate daily report (plain text)

Examples:
  $0 heartbeat
  $0 daily
  $0 all

Files:
  $MEMORY_DIR/agent-status.json
  $MEMORY_DIR/active-tasks.json
  $MEMORY_DIR/TASK-BOARD.md

EOF
            ;;
    esac
}

main "$@"
