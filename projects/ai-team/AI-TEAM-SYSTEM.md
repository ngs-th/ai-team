# 🤖 AI Team System Documentation

System for managing AI agents and tasks using SQLite database.

## Overview

The AI Team System coordinates multiple AI agents working on projects. It tracks:
- Agent status and heartbeats
- Task assignments and progress
- Project status and deadlines
- Historical actions via task history

## Quick Start

### Show Current Status
```bash
# Check all agents
~/clawd/projects/ai-team/update-heartbeat.sh status

# Check system overview
sqlite3 ~/clawd/projects/ai-team/team.db "SELECT * FROM v_dashboard_stats;"
```

### Start Working on a Task
```bash
# When an agent starts a task, update heartbeat
~/clawd/projects/ai-team/update-heartbeat.sh start-task <agent_id> <task_id>

# Example:
~/clawd/projects/ai-team/update-heartbeat.sh start-task dev T-20260202-001
```

### During Long Tasks (10+ minutes)
```bash
# Start periodic heartbeat updates every 10 minutes
~/clawd/projects/ai-team/update-heartbeat.sh periodic-start <agent_id>

# Stop when done
~/clawd/projects/ai-team/update-heartbeat.sh periodic-stop <agent_id>
```

### Complete a Task
```bash
# Mark task as complete and update agent
~/clawd/projects/ai-team/update-heartbeat.sh complete <agent_id> <task_id>
```

## Directory Structure

```
~/clawd/projects/ai-team/
├── team.db                      # Main SQLite database
├── update-heartbeat.sh          # Heartbeat management script
└── AI-TEAM-SYSTEM.md           # This documentation

~/clawd/monitoring/scripts/
└── ai-team-monitor.sh          # Monitoring and reporting script
```

## Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `agents` | AI agent profiles and status |
| `tasks` | Task definitions and progress |
| `projects` | Project containers |
| `task_history` | Audit log of all task changes |
| `task_dependencies` | Task dependency relationships |

### Views

| View | Purpose |
|------|---------|
| `v_agent_status` | Agent heartbeat status with silence detection |
| `v_agent_workload` | Task counts per agent |
| `v_task_summary` | Task overview with urgency |
| `v_task_overview` | Comprehensive task view with due dates |
| `v_project_status` | Project progress summary |
| `v_dashboard_stats` | System-wide statistics |
| `v_daily_summary` | Daily aggregated metrics |
| `v_weekly_report` | Weekly aggregated metrics |

## Monitoring

### Check Heartbeats (Silent Agents >30 min)
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh heartbeat
```

### Check Deadlines
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh deadlines
```

### Check Blocked Tasks
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh blocked
```

### Generate Reports
```bash
# Hourly report
~/clawd/monitoring/scripts/ai-team-monitor.sh hourly

# Daily report
~/clawd/monitoring/scripts/ai-team-monitor.sh daily

# All checks
~/clawd/monitoring/scripts/ai-team-monitor.sh all
```

### Telegram Output (Plain Text)
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh telegram-hourly
~/clawd/monitoring/scripts/ai-team-monitor.sh telegram-daily
```

## Agent Workflow

```
1. AGENT STARTS TASK
   └─→ update-heartbeat.sh start-task <agent> <task>
       └─→ Sets status='active', updates heartbeat

2. DURING TASK (long running)
   ├─→ update-heartbeat.sh periodic-start <agent>  (every 10 min)
   └─→ OR: update-heartbeat.sh update <agent>      (manual)

3. TASK COMPLETE
   └─→ update-heartbeat.sh complete <agent> <task>
       └─→ Sets status='done', progress=100, heartbeat

4. AGENT IDLE
   └─→ Automatically set when no tasks in progress
```

## Useful Queries

### Find Silent Agents (>30 min)
```sql
SELECT id, name, minutes_since_heartbeat 
FROM v_agent_status 
WHERE is_silent = 1;
```

### Overdue Tasks
```sql
SELECT id, title, assignee, days_until_due 
FROM v_task_overview 
WHERE is_overdue = 1;
```

### Tasks Due Today
```sql
SELECT id, title, assignee 
FROM v_task_overview 
WHERE due_status = 'due_today';
```

### Agent Workload
```sql
SELECT * FROM v_agent_workload;
```

### Project Progress
```sql
SELECT * FROM v_project_status;
```

## Cron Setup

### Hourly Monitoring (add to crontab)
```bash
0 * * * * /Users/ngs/clawd/monitoring/scripts/ai-team-monitor.sh hourly >> /Users/ngs/clawd/monitoring/logs/hourly.log 2>&1
```

### Daily Report at 6 PM
```bash
0 18 * * * /Users/ngs/clawd/monitoring/scripts/ai-team-monitor.sh daily >> /Users/ngs/clawd/monitoring/logs/daily.log 2>&1
```

## Troubleshooting

### Check Database Connection
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh db-check
```

### Manual Heartbeat Update
```bash
sqlite3 ~/clawd/projects/ai-team/team.db \
  "UPDATE agents SET last_heartbeat = datetime('now') WHERE id = 'dev';"
```

### View Recent Task History
```sql
SELECT * FROM task_history 
ORDER BY timestamp DESC 
LIMIT 20;
```

## Task Status Values

| Status | Meaning |
|--------|---------|
| `todo` | Not started |
| `in_progress` | Currently working |
| `review` | Pending review |
| `done` | Completed |
| `blocked` | Blocked by dependency |
| `cancelled` | Cancelled |

## Agent Status Values

| Status | Meaning |
|--------|---------|
| `idle` | Available for tasks |
| `active` | Working on task |
| `blocked` | Unable to proceed |
| `offline` | Not responding |
