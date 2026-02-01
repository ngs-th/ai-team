# 🤖 AI Team Dashboard

Real-time dashboard for AI team task and progress tracking. Displays live data from SQLite database with auto-refresh.

## Architecture

- **Frontend**: HTML + Tailwind CSS + Vanilla JavaScript
- **Backend**: Node.js + HTTP server + SQLite3
- **Database**: SQLite (team.db)

## Quick Start

### 1. Start the Server

```bash
cd /Users/ngs/clawd/memory/team
npm start
```

### 2. Open Dashboard

Visit: http://127.0.0.1:5000

The dashboard automatically loads real data from `team.db`.

## Files

| File | Description |
|------|-------------|
| `server.js` | Node.js API server (main entry) |
| `dashboard.html` | Dashboard frontend |
| `team.db` | SQLite database |
| `package.json` | Node dependencies |
| `server.py` | Alternative Python server (if preferred) |
| `README.md` | This file |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Serves the dashboard HTML |
| `GET /api/stats` | Dashboard statistics |
| `GET /api/agents` | List of agents with status |
| `GET /api/tasks` | List of tasks for kanban |
| `GET /api/projects` | List of projects with progress |
| `GET /api/activities` | Recent activity log |
| `GET /api/health` | Health check |

## Auto-Refresh

Dashboard auto-refreshes every **30 seconds**. Manual refresh available via the Refresh button.

## Database Schema

Uses existing `team.db` with tables:
- `agents` - Team members
- `tasks` - Task records
- `projects` - Project definitions
- `task_history` - Activity log

Views:
- `v_dashboard_stats` - Pre-calculated stats
- `v_project_status` - Project progress
- `v_task_summary` - Task summaries
- `v_agent_workload` - Agent workload info

## Current Data

The database contains:
- **9 Agents**: John (PM), Mary (Analyst), Winston (Architect), Amelia (Dev), Sally (UX), Bob (Scrum Master), Quinn (QA), Tom (Tech Writer), Barry (Solo Dev)
- **6 Tasks**: Mix of todo, in-progress, blocked, and done
- **2 Projects**: AI Team System, Dashboard v2
- **Activity Log**: Recent task history

## Troubleshooting

**Dashboard shows "Failed to load data"**
- Ensure server is running: `node server.js`
- Check health endpoint: `curl http://127.0.0.1:5000/api/health`

**No data displayed**
- Database may be empty - add tasks via SQL
- Check browser console for errors

**Port already in use**
- Kill existing process: `pkill -f "node server.js"`
- Or change PORT in server.js

## Alternative: Python Server

If you prefer Python:

```bash
pip3 install flask flask-cors --break-system-packages
python3 server.py
```

## Development

To add/modify data:

```bash
sqlite3 team.db
-- Run SQL commands
```

## What Was Changed

1. **Created `server.js`** - Node.js HTTP server with SQLite API endpoints
2. **Updated `dashboard.html`** - Replaced mockData with fetch() calls to /api/*
3. **Added sample data** - Tasks, projects, activities in team.db
4. **Same UI/Styling** - No visual changes, just real data
5. **Auto-refresh** - Still works every 30 seconds
