#!/bin/bash
# AI Team Monitoring Scripts

TEAM_DIR="$HOME/clawd/memory/team"
LOG_DIR="$HOME/clawd/logs"
mkdir -p "$LOG_DIR"

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_DIR/ai-team-monitor.log"
}

check_heartbeat() {
    log_msg "Checking agent heartbeats"
    cd "$TEAM_DIR" || exit 1
    
    sqlite3 team.db "
        SELECT a.id, a.name, 
            (julianday('now') - julianday(a.last_heartbeat)) * 24 * 60,
            a.current_task_id
        FROM agents a
        WHERE a.status = 'active'
        AND a.last_heartbeat IS NOT NULL
        AND (julianday('now') - julianday(a.last_heartbeat)) * 24 * 60 > 30;
    " | while IFS='|' read -r id name minutes task; do
        msg="🚨 AGENT SILENT: $name (${minutes%.*}m)"
        echo "$msg" >> "$LOG_DIR/alerts.log"
        sqlite3 messages.db "INSERT INTO notifications (notification_id, content) VALUES ('HB-$id-$(date +%s)', '$msg');"
    done
}

check_blocked() {
    log_msg "Checking blocked tasks"
    cd "$TEAM_DIR" || exit 1
    
    sqlite3 team.db "
        SELECT t.id, t.title, 
            (julianday('now') - julianday(t.updated_at)) * 24,
            a.name
        FROM tasks t
        LEFT JOIN agents a ON t.assignee_id = a.id
        WHERE t.status = 'blocked'
        AND (julianday('now') - julianday(t.updated_at)) * 24 > 2;
    " | while IFS='|' read -r id title hours assignee; do
        msg="🚧 BLOCKED: $id - ${title:0:30} (${hours%.*}h)"
        echo "$msg" >> "$LOG_DIR/alerts.log"
        sqlite3 messages.db "INSERT INTO notifications (notification_id, content, context_task_id) VALUES ('BLK-$id-$(date +%s)', '$msg', '$id');"
    done
}

check_deadlines() {
    log_msg "Checking deadlines"
    cd "$TEAM_DIR" || exit 1
    
    # Overdue
    sqlite3 team.db "
        SELECT t.id, t.title, julianday('now') - julianday(t.due_date), a.name
        FROM tasks t LEFT JOIN agents a ON t.assignee_id = a.id
        WHERE t.due_date < DATE('now') AND t.status NOT IN ('done', 'cancelled');
    " | while IFS='|' read -r id title days assignee; do
        msg="⏰ OVERDUE: $id - ${title:0:30} (${days%.*}d)"
        echo "$msg" >> "$LOG_DIR/alerts.log"
        sqlite3 messages.db "INSERT INTO notifications (notification_id, content, context_task_id) VALUES ('OVD-$id-$(date +%s)', '$msg', '$id');"
    done
    
    # Due today
    sqlite3 team.db "
        SELECT t.id, t.title, t.progress, a.name
        FROM tasks t LEFT JOIN agents a ON t.assignee_id = a.id
        WHERE DATE(t.due_date) = DATE('now') AND t.status NOT IN ('done', 'cancelled');
    " | while IFS='|' read -r id title progress assignee; do
        msg="📅 DUE TODAY: $id - ${title:0:30} ($progress%)"
        echo "$msg" >> "$LOG_DIR/alerts.log"
        sqlite3 messages.db "INSERT INTO notifications (notification_id, content, context_task_id) VALUES ('DUE-$id-$(date +%s)', '$msg', '$id');"
    done
}

hourly_report() {
    log_msg "Generating hourly report"
    cd "$TEAM_DIR" || exit 1
    
    stats=$(sqlite3 team.db "
        SELECT 
            COUNT(CASE WHEN status = 'done' AND completed_at >= datetime('now', '-1 hour') THEN 1 END),
            COUNT(CASE WHEN status = 'in_progress' THEN 1 END),
            COUNT(CASE WHEN status = 'blocked' THEN 1 END)
        FROM tasks;
    ")
    
    IFS='|' read -r done recent blocked <<< "$stats"
    
    report="📊 HOURLY ($(date '+%H:%M'))
✅ Done: ${done:-0} | 🔄 Progress: ${recent:-0} | 🚧 Blocked: ${blocked:-0}"
    
    echo "$report" | tee -a "$LOG_DIR/reports.log"
}

daily_report() {
    log_msg "Generating daily report"
    cd "$TEAM_DIR" || exit 1
    
    stats=$(sqlite3 team.db "
        SELECT 
            COUNT(CASE WHEN DATE(created_at) = DATE('now') THEN 1 END),
            COUNT(CASE WHEN DATE(completed_at) = DATE('now') THEN 1 END),
            COUNT(CASE WHEN status = 'in_progress' THEN 1 END),
            COUNT(CASE WHEN status = 'blocked' THEN 1 END)
        FROM tasks;
    ")
    
    IFS='|' read -r created completed progress blocked <<< "$stats"
    
    agents=$(sqlite3 team.db "SELECT name FROM agents WHERE status != 'idle' ORDER BY name;" | tr '\n' ', ')
    
    report="📅 DAILY ($(date '+%Y-%m-%d'))
🆕 New: ${created:-0} | ✅ Done: ${completed:-0}
🔄 Progress: ${progress:-0} | 🚧 Blocked: ${blocked:-0}
👥 Active: ${agents:-None}"
    
    echo "$report" | tee -a "$LOG_DIR/reports.log"
}

# Main
case "$1" in
    heartbeat) check_heartbeat ;;
    blocked) check_blocked ;;
    deadlines) check_deadlines ;;
    hourly) hourly_report ;;
    daily) daily_report ;;
    *) echo "Usage: $0 {heartbeat|blocked|deadlines|hourly|daily}" ; exit 1 ;;
esac
