#!/bin/bash
#
# 🤖 AI Team Monitor Script (SQLite Version)
# Monitors agent heartbeats, deadlines, and generates reports
# Updated: 2026-02-02 - Now uses SQLite instead of JSON files
#

set -e

# Configuration
DB_PATH="${HOME}/clawd/projects/ai-team/team.db"
ALERT_THRESHOLD_MINUTES=30
DATE_FORMAT="+%Y-%m-%d %H:%M:%S"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }

# Check if sqlite3 is available
if ! command -v sqlite3 &> /dev/null; then
    log_error "sqlite3 is required but not installed."
    exit 1
fi

# Check if database exists
if [[ ! -f "$DB_PATH" ]]; then
    log_error "Database not found: $DB_PATH"
    exit 1
fi

# ====================
# Heartbeat Check
# ====================
check_heartbeats() {
    log_info "Checking agent heartbeats..."
    
    local current_time=$(date +%s)
    local alert_threshold=$((ALERT_THRESHOLD_MINUTES * 60))
    local silent_agents=()
    
    # Query active agents and their last heartbeat
    local query="SELECT id, name, last_heartbeat, 
        (strftime('%s', 'now') - strftime('%s', last_heartbeat)) as seconds_since
        FROM agents 
        WHERE status='active'"
    
    while IFS='|' read -r agent_id agent_name last_heartbeat seconds_since; do
        if [[ -n "$seconds_since" && "$seconds_since" =~ ^[0-9]+$ ]]; then
            if [[ $seconds_since -gt $alert_threshold ]]; then
                local minutes=$((seconds_since / 60))
                silent_agents+=("⚠️ $agent_name ($agent_id): Silent for ${minutes}m")
            fi
        fi
    done < <(sqlite3 "$DB_PATH" "$query" 2>/dev/null || echo "")
    
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
    
    local overdue_tasks=()
    
    # Query tasks with upcoming or past due dates
    local query="SELECT t.id, t.title, t.due_date, a.name as assignee,
        (strftime('%s', t.due_date) - strftime('%s', 'now')) as seconds_until
        FROM tasks t
        LEFT JOIN agents a ON t.assignee_id = a.id
        WHERE t.status IN ('todo', 'in_progress')
        AND t.due_date IS NOT NULL
        ORDER BY t.due_date ASC"
    
    while IFS='|' read -r task_id task_title due_date assignee seconds_until; do
        if [[ -n "$seconds_until" && "$seconds_until" =~ ^-?[0-9]+$ ]]; then
            if [[ $seconds_until -lt 0 ]]; then
                # Overdue
                local overdue_min=$(( -seconds_until / 60 ))
                local overdue_hours=$((overdue_min / 60))
                if [[ $overdue_hours -gt 0 ]]; then
                    overdue_tasks+=("⏰ $task_id: $task_title ($assignee) - Overdue by ${overdue_hours}h")
                else
                    overdue_tasks+=("⏰ $task_id: $task_title ($assignee) - Overdue by ${overdue_min}m")
                fi
            elif [[ $seconds_until -lt 86400 ]]; then
                # Due within 24 hours
                local hours_until=$((seconds_until / 3600))
                log_warn "Due soon: $task_id ($hours_until hours remaining)"
            fi
        fi
    done < <(sqlite3 "$DB_PATH" "$query" 2>/dev/null || echo "")
    
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
    
    local blocked_tasks=()
    
    # Query blocked tasks
    local query="SELECT t.id, t.title, t.blocked_by, a.name as assignee
        FROM tasks t
        LEFT JOIN agents a ON t.assignee_id = a.id
        WHERE t.status = 'blocked'"
    
    while IFS='|' read -r task_id task_title blocked_by assignee; do
        blocked_tasks+=("🚧 $task_id: $task_title ($assignee) - Blocked by: ${blocked_by:-unknown}")
    done < <(sqlite3 "$DB_PATH" "$query" 2>/dev/null || echo "")
    
    # Also check tasks with blocked_by set but status not blocked
    local query2="SELECT t.id, t.title, t.blocked_by, a.name as assignee, t.status
        FROM tasks t
        LEFT JOIN agents a ON t.assignee_id = a.id
        WHERE t.blocked_by IS NOT NULL AND t.blocked_by != ''"
    
    while IFS='|' read -r task_id task_title blocked_by assignee status; do
        if [[ "$status" != "blocked" ]]; then
            blocked_tasks+=("⚠️ $task_id: $task_title ($assignee) - Has blocker but status='$status': $blocked_by")
        fi
    done < <(sqlite3 "$DB_PATH" "$query2" 2>/dev/null || echo "")
    
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
    
    # Query dashboard stats
    local stats=$(sqlite3 "$DB_PATH" "SELECT * FROM v_dashboard_stats" 2>/dev/null || echo "")
    
    if [[ -z "$stats" ]]; then
        log_error "Failed to fetch dashboard stats"
        return 1
    fi
    
    # Parse stats (pipe-delimited)
    IFS='|' read -r total_agents active_agents idle_agents blocked_agents \
        total_projects active_projects total_tasks \
        todo_tasks in_progress_tasks completed_tasks blocked_tasks \
        avg_progress due_today overdue_tasks <<< "$stats"
    
    cat << EOF

📊 **AI Team Hourly Report**
$(date "$DATE_FORMAT")

**Tasks:**
• Total: $total_tasks | In Progress: $in_progress_tasks | Done: $completed_tasks | Blocked: $blocked_tasks

**Agents:**
• Active: $active_agents | Idle: $idle_agents

$(if [[ $blocked_tasks -gt 0 ]]; then echo "⚠️ Attention: $blocked_tasks blocked task(s) need help"; fi)
$(if [[ $overdue_tasks -gt 0 ]]; then echo "⏰ Warning: $overdue_tasks overdue task(s)"; fi)
$(if [[ $due_today -gt 0 ]]; then echo "📅 Due today: $due_today task(s)"; fi)

EOF
}

generate_daily_report() {
    log_info "Generating daily report..."
    
    # Get dashboard stats
    local stats=$(sqlite3 "$DB_PATH" "SELECT * FROM v_dashboard_stats" 2>/dev/null || echo "")
    
    if [[ -z "$stats" ]]; then
        log_error "Failed to fetch dashboard stats"
        return 1
    fi
    
    IFS='|' read -r total_agents active_agents idle_agents blocked_agents \
        total_projects active_projects total_tasks \
        todo_tasks in_progress_tasks completed_tasks blocked_tasks \
        avg_progress due_today overdue_tasks <<< "$stats"
    
    # Get tasks completed today
    local completed_today=$(sqlite3 "$DB_PATH" "
        SELECT COUNT(*) FROM tasks 
        WHERE status = 'done' 
        AND DATE(completed_at) = DATE('now')" 2>/dev/null || echo "0")
    
    # Get active agents with their current tasks
    local active_agent_tasks=$(sqlite3 "$DB_PATH" "
        SELECT a.name, t.title 
        FROM agents a 
        LEFT JOIN tasks t ON a.current_task_id = t.id 
        WHERE a.status = 'active'" 2>/dev/null || echo "")
    
    cat << EOF

📊 **AI Team Daily Summary**
$(date "$DATE_FORMAT")

**Today's Progress:**
• Tasks Completed: $completed_today
• Tasks In Progress: $in_progress_tasks
• Blocked Tasks: $blocked_tasks
• Overdue Tasks: $overdue_tasks

**Active Agents:**
$(if [[ -z "$active_agent_tasks" ]]; then 
    echo "None"; 
else 
    while IFS='|' read -r name task; do
        echo "• $name: ${task:-idle}"
    done <<< "$active_agent_tasks"
fi)

$(if [[ $blocked_tasks -gt 0 ]]; then 
    echo "🚧 **Blocked Tasks Need Attention:**"
    sqlite3 "$DB_PATH" "SELECT '• ' || id || ': ' || title FROM tasks WHERE status = 'blocked'" 2>/dev/null || echo ""
fi)

**Summary:** $(if [[ $blocked_tasks -eq 0 && $completed_today -gt 0 ]]; then echo "✅ Good progress today!"; elif [[ $blocked_tasks -gt 0 ]]; then echo "⚠️ Need to unblock tasks"; elif [[ $overdue_tasks -gt 0 ]]; then echo "⏰ Address overdue tasks"; else echo "📋 Steady progress"; fi)

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
        db-check)
            log_info "Checking database connection..."
            if sqlite3 "$DB_PATH" "SELECT 1" > /dev/null 2>&1; then
                log_success "Database connected: $DB_PATH"
                local count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM agents" 2>/dev/null || echo "0")
                log_info "Agents: $count | Tasks: $(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM tasks" 2>/dev/null || echo "0")"
            else
                log_error "Failed to connect to database"
                exit 1
            fi
            ;;
        *)
            cat << EOF
🤖 AI Team Monitor (SQLite Version)

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
  db-check        Verify database connection

Examples:
  $0 heartbeat
  $0 daily
  $0 all

Database:
  $DB_PATH

EOF
            ;;
    esac
}

main "$@"
