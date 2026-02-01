# ⏰ AI Team - Cron Monitoring System

**Version:** 1.0.0  
**Created:** 2026-02-01  
**Status:** Design Proposal

---

## 🎯 เป้าหมาย

1. ติดตามสถานะงานและ Agent อัตโนมัติ
2. แจ้งเตือนเมื่อมีปัญหา (overdue, silent, blocked)
3. สรุปรายงานตามกำหนดเวลา
4. ทุกการแจ้งเตือนส่งไป Telegram

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CRON SCHEDULER                               │
│                   (OpenClaw Gateway)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    ┌─────▼─────┐      ┌─────▼─────┐      ┌─────▼─────┐
    │  Every    │      │  Every    │      │   Daily   │
    │  5 mins   │      │  30 mins  │      │  08:00    │
    └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Check Agent     │  │ Check Task      │  │ Generate        │
│ Heartbeat       │  │ Deadlines       │  │ Daily Report    │
│                 │  │                 │  │                 │
│ • Silent > 30m  │  │ • Due today     │  │ • Summary       │
│ • Stuck > 1h    │  │ • Overdue       │  │ • Metrics       │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      MONITORING ENGINE        │
              │  ~/clawd/monitoring/          │
              │  • monitor.py                 │
              │  • alerts.py                  │
              │  • reports.py                 │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    ALERT RULES ENGINE         │
              │  Check conditions → Actions   │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │   NOTIFICATION SENDER         │
              │  • Telegram (main)            │
              │  • Dashboard update           │
              └───────────────────────────────┘
```

---

## 📁 โครงสร้างไฟล์

```
~/clawd/
├── monitoring/
│   ├── __init__.py
│   ├── config.yaml           # ตั้งค่า monitoring rules
│   ├── monitor.py            # Main monitoring engine
│   ├── alerts.py             # Alert generation
│   ├── reports.py            # Report generation
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── agent_rules.py    # Rules สำหรับ Agents
│   │   ├── task_rules.py     # Rules สำหรับ Tasks
│   │   └── project_rules.py  # Rules สำหรับ Projects
│   └── templates/
│       ├── alert_*.md        # Templates สำหรับ alerts
│       └── report_*.md       # Templates สำหรับ reports
│
├── memory/team/
│   ├── team.db
│   └── monitoring_state.json # เก็บสถานะล่าสุด
│
└── cron/
    └── ai-team-monitor.yaml  # Cron job definitions
```

---

## 🗄️ Database Schema (เพิ่มเติม)

```sql
-- Monitoring state tracking
CREATE TABLE monitoring_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_type TEXT NOT NULL,        -- 'agent_heartbeat', 'task_deadline', etc.
    last_check DATETIME NOT NULL,
    next_check DATETIME,
    findings TEXT,                    -- JSON ของปัญหาที่เจอ
    alert_sent BOOLEAN DEFAULT FALSE,
    alert_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Alert history
CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL UNIQUE,
    alert_type TEXT NOT NULL,         -- 'agent_silent', 'task_overdue', etc.
    severity TEXT,                    -- 'info', 'warning', 'critical'
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    related_task_id TEXT,
    related_agent_id TEXT,
    status TEXT DEFAULT 'active',     -- 'active', 'acknowledged', 'resolved'
    acknowledged_by TEXT,
    acknowledged_at DATETIME,
    resolved_at DATETIME,
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_channel TEXT DEFAULT 'telegram',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_monitoring_type ON monitoring_state(check_type);
CREATE INDEX idx_monitoring_time ON monitoring_state(last_check);
CREATE INDEX idx_alerts_status ON alert_history(status);
CREATE INDEX idx_alerts_type ON alert_history(alert_type);
```

---

## ⏰ Cron Schedule

```yaml
# ~/clawd/cron/ai-team-monitor.yaml

jobs:
  # ทุก 5 นาที: ตรวจสอบ Agent heartbeat
  - name: "check-agent-heartbeat"
    schedule: "*/5 * * * *"
    action: "exec"
    command: "python3 ~/clawd/monitoring/monitor.py --check agents --alert-silent"
    
  # ทุก 10 นาที: ตรวจสอบงานที่ติด
  - name: "check-blocked-tasks"
    schedule: "*/10 * * * *"
    action: "exec"
    command: "python3 ~/clawd/monitoring/monitor.py --check tasks --status blocked --alert"
    
  # ทุก 30 นาที: ตรวจสอบ deadline
  - name: "check-deadlines"
    schedule: "*/30 * * * *"
    action: "exec"
    command: "python3 ~/clawd/monitoring/monitor.py --check deadlines --alert-due --alert-overdue"
    
  # ทุกชั่วโมง: สรุปสถานะ
  - name: "hourly-summary"
    schedule: "0 * * * *"
    action: "exec"
    command: "python3 ~/clawd/monitoring/reports.py --type hourly --send-telegram"
    
  # ทุกวัน 08:00: รายงานประจำวัน
  - name: "daily-morning-report"
    schedule: "0 8 * * *"
    action: "exec"
    command: "python3 ~/clawd/monitoring/reports.py --type daily --send-telegram"
    
  # ทุกวัน 18:00: สรุปผลงานวัน
  - name: "daily-evening-summary"
    schedule: "0 18 * * *"
    action: "exec"
    command: "python3 ~/clawd/monitoring/reports.py --type daily-summary --send-telegram"
    
  # ทุกวันจันทร์ 09:00: รายงานสัปดาห์
  - name: "weekly-report"
    schedule: "0 9 * * 1"
    action: "exec"
    command: "python3 ~/clawd/monitoring/reports.py --type weekly --send-telegram"
    
  # ทุกวันที่ 1 ของเดือน: รายงานเดือน
  - name: "monthly-report"
    schedule: "0 9 1 * *"
    action: "exec"
    command: "python3 ~/clawd/monitoring/reports.py --type monthly --send-telegram"
```

---

## 🔍 Monitoring Rules

### Rule 1: Agent Heartbeat Check

```python
# ~/clawd/monitoring/rules/agent_rules.py

def check_agent_heartbeat(db, silent_threshold_minutes=30):
    """
    ตรวจสอบว่า Agent เงียบไปนานเกินไปหรือไม่
    """
    cursor = db.cursor()
    cursor.execute('''
        SELECT id, name, role, last_heartbeat, current_task_id,
               julianday('now') - julianday(last_heartbeat) * 24 * 60 as minutes_silent
        FROM agents
        WHERE status = 'active'
        AND last_heartbeat IS NOT NULL
        AND (julianday('now') - julianday(last_heartbeat)) * 24 * 60 > ?
    ''', (silent_threshold_minutes,))
    
    silent_agents = []
    for row in cursor.fetchall():
        silent_agents.append({
            'agent_id': row[0],
            'name': row[1],
            'role': row[2],
            'minutes_silent': row[5],
            'current_task': row[4]
        })
    
    return silent_agents


def check_agent_stuck(db, stuck_threshold_minutes=60):
    """
    ตรวจสอบว่า Agent ทำงานนานเกินไปโดยไม่มี progress
    """
    cursor = db.cursor()
    cursor.execute('''
        SELECT a.id, a.name, t.id, t.title, t.progress, t.started_at,
               julianday('now') - julianday(t.started_at) * 24 * 60 as minutes_working
        FROM agents a
        JOIN tasks t ON a.current_task_id = t.id
        WHERE a.status = 'active'
        AND t.status = 'in_progress'
        AND t.started_at IS NOT NULL
        AND (julianday('now') - julianday(t.started_at)) * 24 * 60 > ?
        AND (julianday('now') - julianday(t.updated_at)) * 24 * 60 > ?
    ''', (stuck_threshold_minutes, stuck_threshold_minutes))
    
    stuck_agents = []
    for row in cursor.fetchall():
        stuck_agents.append({
            'agent_id': row[0],
            'name': row[1],
            'task_id': row[2],
            'task_title': row[3],
            'progress': row[4],
            'minutes_working': row[6]
        })
    
    return stuck_agents
```

### Rule 2: Task Deadline Check

```python
# ~/clawd/monitoring/rules/task_rules.py

def check_overdue_tasks(db):
    """
    ตรวจสอบงานที่เลยกำหนด
    """
    cursor = db.cursor()
    cursor.execute('''
        SELECT t.id, t.title, t.due_date, t.status, t.assignee_id, a.name,
               julianday('now') - julianday(t.due_date) as days_overdue
        FROM tasks t
        LEFT JOIN agents a ON t.assignee_id = a.id
        WHERE t.due_date < DATE('now')
        AND t.status NOT IN ('done', 'cancelled')
        ORDER BY t.due_date
    ''')
    
    overdue = []
    for row in cursor.fetchall():
        overdue.append({
            'task_id': row[0],
            'title': row[1],
            'due_date': row[2],
            'status': row[3],
            'assignee': row[5] or 'Unassigned',
            'days_overdue': row[6]
        })
    
    return overdue


def check_due_today_tasks(db):
    """
    ตรวจสอบงานที่ครบกำหนดวันนี้
    """
    cursor = db.cursor()
    cursor.execute('''
        SELECT t.id, t.title, t.due_date, t.status, t.progress, a.name
        FROM tasks t
        LEFT JOIN agents a ON t.assignee_id = a.id
        WHERE DATE(t.due_date) = DATE('now')
        AND t.status NOT IN ('done', 'cancelled')
        ORDER BY t.priority DESC
    ''')
    
    due_today = []
    for row in cursor.fetchall():
        due_today.append({
            'task_id': row[0],
            'title': row[1],
            'due_date': row[2],
            'status': row[3],
            'progress': row[4],
            'assignee': row[5] or 'Unassigned'
        })
    
    return due_today


def check_due_soon_tasks(db, days=2):
    """
    ตรวจสอบงานที่จะครบกำหนดเร็วๆ นี้
    """
    cursor = db.cursor()
    cursor.execute('''
        SELECT t.id, t.title, t.due_date, t.status, t.progress, a.name
        FROM tasks t
        LEFT JOIN agents a ON t.assignee_id = a.id
        WHERE DATE(t.due_date) BETWEEN DATE('now') AND DATE('now', '+{} days')
        AND DATE(t.due_date) > DATE('now')
        AND t.status NOT IN ('done', 'cancelled')
        ORDER BY t.due_date
    '''.format(days))
    
    due_soon = []
    for row in cursor.fetchall():
        due_soon.append({
            'task_id': row[0],
            'title': row[1],
            'due_date': row[2],
            'status': row[3],
            'progress': row[4],
            'assignee': row[5] or 'Unassigned'
        })
    
    return due_soon


def check_blocked_tasks(db, blocked_threshold_hours=2):
    """
    ตรวจสอบงานที่ติดนานเกินไป
    """
    cursor = db.cursor()
    cursor.execute('''
        SELECT t.id, t.title, t.blocked_by, t.notes, a.name,
               julianday('now') - julianday(t.updated_at) * 24 as hours_blocked
        FROM tasks t
        LEFT JOIN agents a ON t.assignee_id = a.id
        WHERE t.status = 'blocked'
        AND (julianday('now') - julianday(t.updated_at)) * 24 > ?
        ORDER BY t.updated_at
    ''', (blocked_threshold_hours,))
    
    blocked = []
    for row in cursor.fetchall():
        blocked.append({
            'task_id': row[0],
            'title': row[1],
            'blocked_by': row[2],
            'notes': row[3],
            'assignee': row[4] or 'Unassigned',
            'hours_blocked': row[5]
        })
    
    return blocked
```

### Rule 3: Project Health Check

```python
# ~/clawd/monitoring/rules/project_rules.py

def check_project_health(db):
    """
    ตรวจสอบสุขภาพโปรเจค
    """
    cursor = db.cursor()
    
    # Get projects with stats
    cursor.execute('''
        SELECT 
            p.id, p.name, p.end_date,
            COUNT(t.id) as total_tasks,
            COUNT(CASE WHEN t.status = 'done' THEN 1 END) as completed,
            COUNT(CASE WHEN t.status = 'blocked' THEN 1 END) as blocked,
            ROUND(100.0 * COUNT(CASE WHEN t.status = 'done' THEN 1 END) / 
                  NULLIF(COUNT(t.id), 0), 1) as progress_pct,
            julianday(p.end_date) - julianday('now') as days_remaining
        FROM projects p
        LEFT JOIN tasks t ON p.id = t.project_id
        WHERE p.status = 'active'
        GROUP BY p.id
    ''')
    
    alerts = []
    for row in cursor.fetchall():
        project = {
            'id': row[0],
            'name': row[1],
            'end_date': row[2],
            'total_tasks': row[3],
            'completed': row[4],
            'blocked': row[5],
            'progress_pct': row[6] or 0,
            'days_remaining': row[7]
        }
        
        # Check if project is at risk
        if project['days_remaining'] and project['days_remaining'] < 0:
            alerts.append({
                'type': 'project_overdue',
                'project': project['name'],
                'message': f"Project '{project['name']}' is overdue by {abs(int(project['days_remaining']))} days"
            })
        elif project['progress_pct'] < 50 and project['days_remaining'] and project['days_remaining'] < 3:
            alerts.append({
                'type': 'project_at_risk',
                'project': project['name'],
                'message': f"Project '{project['name']}' at risk: {project['progress_pct']}% done, {int(project['days_remaining'])} days left"
            })
        elif project['blocked'] > project['total_tasks'] * 0.3:  # More than 30% blocked
            alerts.append({
                'type': 'project_many_blocked',
                'project': project['name'],
                'message': f"Project '{project['name']}' has {project['blocked']}/{project['total_tasks']} tasks blocked"
            })
    
    return alerts
```

---

## 📱 Alert Templates

### Alert: Agent Silent

```markdown
# Template: alert_agent_silent.md

🚨 AGENT SILENT ALERT

Agent: {{agent_name}} ({{agent_role}})
Status: Has not reported progress for {{minutes_silent}} minutes

Current Task: {{task_id}}
Task: {{task_title}}
Progress: {{task_progress}}%

Last Heartbeat: {{last_heartbeat}}
Expected Update: Every 10 minutes

Actions:
• [Ping Agent] [Check Status] [Reassign Task]

This is an automated alert from AI Team Monitoring System.
```

### Alert: Task Overdue

```markdown
# Template: alert_task_overdue.md

⏰ TASK OVERDUE

Task: {{task_id}}
Title: {{task_title}}
Assignee: {{assignee}}

Due Date: {{due_date}}
Days Overdue: {{days_overdue}}
Current Status: {{status}}
Progress: {{progress}}%

This task was due {{days_overdue}} days ago and has not been completed.

Actions:
• [Extend Deadline] [Reassign] [Mark Complete] [Cancel Task]

This is an automated alert from AI Team Monitoring System.
```

### Alert: Task Blocked

```markdown
# Template: alert_task_blocked.md

🚧 TASK BLOCKED

Task: {{task_id}}
Title: {{task_title}}
Assignee: {{assignee}}
Blocked For: {{hours_blocked}} hours

Blocker: {{blocked_by}}
Notes: {{notes}}

This task has been blocked for {{hours_blocked}} hours and needs attention.

Actions:
• [View Details] [Unblock] [Reassign] [Escalate]

This is an automated alert from AI Team Monitoring System.
```

---

## 🐍 Main Monitoring Script

```python
#!/usr/bin/env python3
"""
AI Team Monitoring Engine
Main entry point for all monitoring tasks
"""

#!/usr/bin/env python3
import argparse
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import sys

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "memory" / "team"))

from rules.agent_rules import check_agent_heartbeat, check_agent_stuck
from rules.task_rules import check_overdue_tasks, check_due_today_tasks, check_blocked_tasks
from rules.project_rules import check_project_health

TEAM_DB = Path(__file__).parent.parent / "memory" / "team" / "team.db"
MESSAGES_DB = Path(__file__).parent.parent / "memory" / "team" / "messages.db"

class MonitoringEngine:
    def __init__(self):
        self.team_db = sqlite3.connect(TEAM_DB)
        self.team_db.row_factory = sqlite3.Row
        
    def close(self):
        self.team_db.close()
        
    def check_all(self, send_alerts=True):
        """Run all monitoring checks"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'alerts': []
        }
        
        # Check 1: Silent Agents
        silent = check_agent_heartbeat(self.team_db, silent_threshold_minutes=30)
        for agent in silent:
            alert = {
                'type': 'agent_silent',
                'severity': 'warning',
                'title': f"Agent {agent['name']} is silent",
                'message': f"{agent['name']} has not reported for {int(agent['minutes_silent'])} minutes",
                'data': agent
            }
            results['alerts'].append(alert)
            if send_alerts:
                self._send_alert(alert)
        
        # Check 2: Stuck Agents
        stuck = check_agent_stuck(self.team_db, stuck_threshold_minutes=60)
        for agent in stuck:
            alert = {
                'type': 'agent_stuck',
                'severity': 'warning',
                'title': f"Agent {agent['name']} may be stuck",
                'message': f"Working on '{agent['task_title']}' for {int(agent['minutes_working'])} mins with no progress",
                'data': agent
            }
            results['alerts'].append(alert)
            if send_alerts:
                self._send_alert(alert)
        
        # Check 3: Overdue Tasks
        overdue = check_overdue_tasks(self.team_db)
        for task in overdue:
            alert = {
                'type': 'task_overdue',
                'severity': 'critical' if task['days_overdue'] > 1 else 'warning',
                'title': f"Task {task['task_id']} is overdue",
                'message': f"'{task['title']}' is {int(task['days_overdue'])} days overdue",
                'data': task
            }
            results['alerts'].append(alert)
            if send_alerts:
                self._send_alert(alert)
        
        # Check 4: Due Today
        due_today = check_due_today_tasks(self.team_db)
        for task in due_today:
            if task['progress'] < 100:
                alert = {
                    'type': 'task_due_today',
                    'severity': 'info',
                    'title': f"Task {task['task_id']} due today",
                    'message': f"'{task['title']}' is due today ({task['progress']}% complete)",
                    'data': task
                }
                results['alerts'].append(alert)
                if send_alerts:
                    self._send_alert(alert)
        
        # Check 5: Blocked Tasks
        blocked = check_blocked_tasks(self.team_db, blocked_threshold_hours=2)
        for task in blocked:
            alert = {
                'type': 'task_blocked',
                'severity': 'warning',
                'title': f"Task {task['task_id']} blocked",
                'message': f"'{task['title']}' has been blocked for {int(task['hours_blocked'])} hours",
                'data': task
            }
            results['alerts'].append(alert)
            if send_alerts:
                self._send_alert(alert)
        
        # Check 6: Project Health
        project_alerts = check_project_health(self.team_db)
        for proj_alert in project_alerts:
            alert = {
                'type': proj_alert['type'],
                'severity': 'warning',
                'title': f"Project Alert: {proj_alert['project']}",
                'message': proj_alert['message'],
                'data': proj_alert
            }
            results['alerts'].append(alert)
            if send_alerts:
                self._send_alert(alert)
        
        # Log monitoring run
        self._log_monitoring_run(results)
        
        return results
    
    def _send_alert(self, alert):
        """Send alert to Telegram"""
        # Format message for Telegram
        emoji = {
            'critical': '🔴',
            'warning': '🟡',
            'info': '🔵'
        }.get(alert['severity'], '⚪')
        
        message = f"""
{emoji} {alert['title'].upper()}

{alert['message']}

Type: {alert['type']}
Time: {datetime.now().strftime('%H:%M:%S')}

[View Details] [Acknowledge] [Resolve]
"""
        
        # In real implementation, use message tool
        print(f"\n[TELEGRAM ALERT SENT]\n{message}\n{'='*50}")
        
        # Store in database
        self._store_alert(alert)
    
    def _store_alert(self, alert):
        """Store alert in database"""
        # This would store in messages.db alert_history table
        pass
    
    def _log_monitoring_run(self, results):
        """Log this monitoring run"""
        # Store in monitoring_state table
        pass


def main():
    parser = argparse.ArgumentParser(description='AI Team Monitoring Engine')
    parser.add_argument('--check', choices=['all', 'agents', 'tasks', 'deadlines', 'projects'],
                       default='all', help='What to check')
    parser.add_argument('--alert-silent', action='store_true', help='Alert on silent agents')
    parser.add_argument('--alert-due', action='store_true', help='Alert on due tasks')
    parser.add_argument('--alert-overdue', action='store_true', help='Alert on overdue tasks')
    parser.add_argument('--no-alert', action='store_true', help='Do not send alerts (dry run)')
    
    args = parser.parse_args()
    
    engine = MonitoringEngine()
    
    try:
        print(f"🔍 Starting monitoring check: {args.check}")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        results = engine.check_all(send_alerts=not args.no_alert)
        
        print(f"\n✅ Check complete!")
        print(f"🚨 Alerts generated: {len(results['alerts'])}")
        
        for alert in results['alerts']:
            print(f"  - [{alert['severity'].upper()}] {alert['title']}")
        
    finally:
        engine.close()


if __name__ == '__main__':
    main()
```

---

## 📊 Report Generation

```python
#!/usr/bin/env python3
"""
AI Team Report Generator
Generate periodic reports for Telegram
"""

import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

TEAM_DB = Path(__file__).parent.parent / "memory" / "team" / "team.db"

class ReportGenerator:
    def __init__(self):
        self.db = sqlite3.connect(TEAM_DB)
        self.db.row_factory = sqlite3.Row
        
    def generate_hourly_report(self):
        """Generate hourly status report"""
        cursor = self.db.cursor()
        
        # Get stats from last hour
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN status = 'done' AND completed_at >= datetime('now', '-1 hour') THEN 1 END) as completed_last_hour,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                COUNT(CASE WHEN status = 'blocked' THEN 1 END) as blocked
            FROM tasks
        ''')
        row = cursor.fetchone()
        
        report = f"""
📊 HOURLY STATUS UPDATE ({datetime.now().strftime('%H:%M')})

✅ Completed last hour: {row[0] or 0}
🔄 In progress: {row[1] or 0}
🚧 Blocked: {row[2] or 0}

Active agents will continue working.
"""
        return report
    
    def generate_daily_report(self):
        """Generate daily summary report"""
        cursor = self.db.cursor()
        
        # Today's stats
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN DATE(created_at) = DATE('now') THEN 1 END) as created_today,
                COUNT(CASE WHEN DATE(completed_at) = DATE('now') THEN 1 END) as completed_today,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                COUNT(CASE WHEN status = 'todo' THEN 1 END) as todo,
                COUNT(CASE WHEN status = 'blocked' THEN 1 END) as blocked,
                COUNT(CASE WHEN status = 'done' THEN 1 END) as total_done
            FROM tasks
        ''')
        row = cursor.fetchone()
        
        # Agent stats
        cursor.execute('''
            SELECT name, total_tasks_completed, status
            FROM agents
            WHERE status != 'idle'
            ORDER BY total_tasks_completed DESC
        ''')
        active_agents = cursor.fetchall()
        
        report = f"""
📅 DAILY REPORT - {datetime.now().strftime('%Y-%m-%d')}

📊 TASK SUMMARY
━━━━━━━━━━━━━━━━━━━━
🆕 Created today: {row[0] or 0}
✅ Completed today: {row[1] or 0}
🔄 In progress: {row[2] or 0}
⬜ Todo: {row[3] or 0}
🚧 Blocked: {row[4] or 0}
📈 Total done: {row[5] or 0}

👥 ACTIVE AGENTS
━━━━━━━━━━━━━━━━━━━━
"""
        for agent in active_agents:
            status_emoji = '🟢' if agent[2] == 'active' else '🟡' if agent[2] == 'blocked' else '⚪'
            report += f"{status_emoji} {agent[0]}: {agent[1]} tasks completed\n"
        
        # Check for alerts
        cursor.execute('''
            SELECT COUNT(*) FROM tasks
            WHERE due_date < DATE('now') AND status NOT IN ('done', 'cancelled')
        ''')
        overdue = cursor.fetchone()[0]
        
        if overdue > 0:
            report += f"\n⚠️ ATTENTION: {overdue} overdue tasks need review\n"
        
        report += "\nKeep up the good work! 💪"
        
        return report
    
    def generate_weekly_report(self):
        """Generate weekly summary"""
        # Similar to daily but for the week
        pass
    
    def send_to_telegram(self, report):
        """Send report to Telegram"""
        print(f"\n[TELEGRAM REPORT SENT]\n{report}\n{'='*50}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', choices=['hourly', 'daily', 'daily-summary', 'weekly', 'monthly'],
                       required=True)
    parser.add_argument('--send-telegram', action='store_true')
    
    args = parser.parse_args()
    
    generator = ReportGenerator()
    
    if args.type == 'hourly':
        report = generator.generate_hourly_report()
    elif args.type in ['daily', 'daily-summary']:
        report = generator.generate_daily_report()
    else:
        report = f"{args.type.upper()} REPORT\n(Feature not implemented)"
    
    if args.send_telegram:
        generator.send_to_telegram(report)
    else:
        print(report)


if __name__ == '__main__':
    main()
```

---

## 🧪 ทดสอบระบบ

```bash
# Test monitoring engine
python3 ~/clawd/monitoring/monitor.py --check all --no-alert

# Test with alerts
python3 ~/clawd/monitoring/monitor.py --check agents --alert-silent

# Generate daily report
python3 ~/clawd/monitoring/reports.py --type daily --send-telegram

# Check specific conditions
python3 ~/clawd/monitoring/monitor.py --check deadlines --alert-due --alert-overdue
```

---

## 📋 สรุป

| Check | Frequency | Action |
|-------|-----------|--------|
| Agent Heartbeat | 5 นาที | แจ้งเตือน Agent เงียบ |
| Blocked Tasks | 10 นาที | แจ้งเตือนงานติดนาน |
| Deadlines | 30 นาที | แจ้งเตือน due/overdue |
| Hourly Summary | ทุกชั่วโมง | สรุปสถานะ |
| Daily Report | 08:00/18:00 | รายงานประจำวัน |
| Weekly Report | จันทร์ 09:00 | รายงานสัปดาห์ |

**ทุกการแจ้งเตือนส่งไป Telegram ทั้งหมด**

**ต้องการให้สร้างไฟล์จริงไหมครับ?** 🎯
