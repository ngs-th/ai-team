# 🤖 AI Team Dashboard

AI Team monitoring dashboard - Pure PHP + SQLite3 implementation.

## Location

This project has been reorganized:

- **Code:** `~/clawd/projects/ai-team/` (this directory)
- **Data:** `~/clawd/memory/team/team.db`

## Files

| File | Description |
|------|-------------|
| `dashboard.php` | Main dashboard (pure PHP, single file) |
| `team_db.py` | CLI tool for database management |
| `README.md` | This file |

## Quick Start

### Run Dashboard

```bash
cd ~/clawd/projects/ai-team
php -S localhost:8080 dashboard.php
```

Then open: http://localhost:8080

### CLI Tool

```bash
cd ~/clawd/projects/ai-team
python3 team_db.py --help
```

## Dashboard Features

- **Auto-refresh:** Every 30 seconds
- **Stats:** Total agents, tasks, projects
- **Agents:** Status, workload, progress
- **Projects:** Progress bars, task counts
- **Tasks:** Full task list with priorities
- **Activity:** Recent task history

## Database

Location: `~/clawd/memory/team/team.db`

Tables:
- `agents` - Team members
- `projects` - Project definitions
- `tasks` - Task records
- `task_history` - Activity log

Views:
- `v_dashboard_stats` - Pre-calculated stats
- `v_project_status` - Project progress
- `v_task_summary` - Task summaries
- `v_agent_workload` - Agent workload info

## No Dependencies

- Pure PHP (built-in SQLite3 extension)
- No frameworks
- No composer packages
- No external libraries
