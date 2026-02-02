#!/usr/bin/env python3
"""
AI Team Database Manager
Manage tasks, agents, and projects for the AI Team
"""

import os
import sqlite3
import json
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

# Set timezone to Bangkok (+7)
os.environ['TZ'] = 'Asia/Bangkok'

DB_PATH = Path(__file__).parent / "team.db"
TELEGRAM_CHANNEL = "1268858185"

def send_telegram_notification(message: str) -> bool:
    """Send notification to Telegram channel using OpenClaw message tool"""
    try:
        result = subprocess.run(
            ["openclaw", "message", "send", "--channel", "telegram", 
             "--target", TELEGRAM_CHANNEL, "--message", message],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[Notification Error] Failed to send Telegram message: {e}")
        return False

class AITeamDB:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        
    def close(self):
        self.conn.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.close()

    # ========== Tasks ==========
    
    def create_task(self, title: str, description: str = "", 
                    assignee_id: str = None, project_id: str = None,
                    priority: str = "normal", estimated_hours: float = None,
                    due_date: str = None) -> str:
        """Create a new task"""
        # MANDATORY: Every task must have a project
        if not project_id:
            raise ValueError("project_id is required - every task must belong to a project")
        
        task_id = f"T-{datetime.now().strftime('%Y%m%d')}-{self._get_next_task_number():03d}"
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO tasks (id, title, description, assignee_id, project_id,
                             priority, estimated_hours, due_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'todo')
        ''', (task_id, title, description, assignee_id, project_id,
              priority, estimated_hours, due_date))
        
        # Log the creation
        cursor.execute('''
            INSERT INTO task_history (task_id, action, notes)
            VALUES (?, 'created', ?)
        ''', (task_id, f"Task created with priority {priority}"))
        
        self.conn.commit()
        
        # Send Telegram notification
        assignee_str = assignee_id if assignee_id else "Unassigned"
        notification = f"🆕 Task {task_id}: {title} created (Assignee: {assignee_str})"
        send_telegram_notification(notification)
        
        return task_id
    
    def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign task to an agent"""
        cursor = self.conn.cursor()
        
        # Update task
        cursor.execute('''
            UPDATE tasks SET assignee_id = ?, status = 'todo', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (agent_id, task_id))
        
        # Update agent stats
        cursor.execute('''
            UPDATE agents SET total_tasks_assigned = total_tasks_assigned + 1,
                            current_task_id = ?, status = 'active',
                            updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (task_id, agent_id))
        
        # Log history
        cursor.execute('''
            INSERT INTO task_history (task_id, agent_id, action, notes)
            VALUES (?, ?, 'assigned', ?)
        ''', (task_id, agent_id, f"Assigned to {agent_id}"))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def start_task(self, task_id: str, agent_id: str = None) -> bool:
        """Start working on a task"""
        cursor = self.conn.cursor()
        
        # Get task info before updating
        cursor.execute('SELECT title, assignee_id FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        task_title = row[0]
        assignee = agent_id or row[1] or "Unknown"
        
        cursor.execute('''
            UPDATE tasks 
            SET status = 'in_progress', started_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (task_id,))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status)
            SELECT id, 'started', 'todo', 'in_progress'
            FROM tasks WHERE id = ?
        ''', (task_id,))
        
        self.conn.commit()
        
        # Send Telegram notification
        notification = f"🚀 Task {task_id} started by {assignee}"
        send_telegram_notification(notification)
        
        return cursor.rowcount > 0
    
    def send_to_review(self, task_id: str) -> bool:
        """Send task to review (in_progress -> review)"""
        cursor = self.conn.cursor()
        
        # Get task info before updating
        cursor.execute('SELECT title, status FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        old_status = row[1]
        if old_status != 'in_progress':
            print(f"⚠️ Task {task_id} must be in_progress to send to review")
            return False
        
        cursor.execute('''
            UPDATE tasks 
            SET status = 'review', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (task_id,))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status)
            VALUES (?, 'updated', 'in_progress', 'review')
        ''', (task_id,))
        
        self.conn.commit()
        
        # Send Telegram notification
        notification = f"👀 Task {task_id} sent for review"
        send_telegram_notification(notification)
        
        return cursor.rowcount > 0
    
    def update_progress(self, task_id: str, progress: int, notes: str = "") -> bool:
        """Update task progress (0-100)"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT progress FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        old_progress = row[0] if row else 0
        
        cursor.execute('''
            UPDATE tasks 
            SET progress = ?, updated_at = CURRENT_TIMESTAMP,
                notes = CASE WHEN ? != '' THEN ? ELSE notes END
            WHERE id = ?
        ''', (progress, notes, notes, task_id))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_progress, new_progress, notes)
            VALUES (?, 'updated', ?, ?, ?)
        ''', (task_id, old_progress, progress, notes))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def complete_task(self, task_id: str) -> bool:
        """Mark task as completed"""
        cursor = self.conn.cursor()
        
        # Get task info before updating
        cursor.execute('SELECT title, started_at FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        task_title = row[0]
        
        # Calculate actual duration if started_at exists
        if row[1]:
            # Calculate duration in minutes
            cursor.execute('''
                UPDATE tasks 
                SET status = 'done', progress = 100, completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    actual_duration_minutes = ROUND((strftime('%s', 'now') - strftime('%s', started_at)) / 60)
                WHERE id = ?
            ''', (task_id,))
        else:
            cursor.execute('''
                UPDATE tasks 
                SET status = 'done', progress = 100, completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (task_id,))
        
        # Update agent stats
        cursor.execute('''
            UPDATE agents 
            SET total_tasks_completed = total_tasks_completed + 1,
                current_task_id = NULL, status = 'idle',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT assignee_id FROM tasks WHERE id = ?)
        ''', (task_id,))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status)
            SELECT id, 'completed', status, 'done'
            FROM tasks WHERE id = ?
        ''', (task_id,))
        
        self.conn.commit()
        
        # Send Telegram notification
        notification = f"✅ Task {task_id} completed"
        send_telegram_notification(notification)
        
        return cursor.rowcount > 0
    
    def block_task(self, task_id: str, reason: str) -> bool:
        """Block a task with reason"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE tasks 
            SET status = 'blocked', blocked_reason = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (reason, task_id))
        
        cursor.execute('''
            UPDATE agents 
            SET status = 'blocked', updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT assignee_id FROM tasks WHERE id = ?)
        ''', (task_id,))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, notes)
            VALUES (?, 'blocked', ?)
        ''', (task_id, reason))
        
        self.conn.commit()
        
        # Send Telegram notification
        notification = f"🚫 Task {task_id} blocked: {reason}"
        send_telegram_notification(notification)
        
        return cursor.rowcount > 0
    
    def unblock_task(self, task_id: str, agent_id: str = None) -> bool:
        """Unblock a task and resume (blocked -> in_progress)"""
        cursor = self.conn.cursor()
        
        # Get task info before updating
        cursor.execute('SELECT title, assignee_id, status FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        if row[2] != 'blocked':
            print(f"⚠️ Task {task_id} is not blocked")
            return False
        
        assignee = agent_id or row[1] or "Unknown"
        
        cursor.execute('''
            UPDATE tasks 
            SET status = 'in_progress', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (task_id,))
        
        cursor.execute('''
            UPDATE agents 
            SET status = 'active', updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT assignee_id FROM tasks WHERE id = ?)
        ''', (task_id,))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status)
            VALUES (?, 'unblocked', 'blocked', 'in_progress')
        ''', (task_id,))
        
        self.conn.commit()
        
        # Send Telegram notification
        notification = f"🔄 Task {task_id} resumed"
        send_telegram_notification(notification)
        
        return cursor.rowcount > 0
    
    def get_tasks(self, status: str = None, assignee: str = None) -> List[Dict]:
        """Get tasks with optional filters"""
        cursor = self.conn.cursor()
        
        query = 'SELECT * FROM v_task_summary WHERE 1=1'
        params = []
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        if assignee:
            query += ' AND assignee_id = ?'
            params.append(assignee)
            
        query += ' ORDER BY due_date, priority'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== Agents ==========
    
    def get_agents(self, status: str = None) -> List[Dict]:
        """Get all agents with their workload"""
        cursor = self.conn.cursor()
        
        query = 'SELECT * FROM v_agent_workload WHERE 1=1'
        params = []
        
        if status:
            query += ' AND status = ?'
            params.append(status)
            
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def update_agent_heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat timestamp"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE agents 
            SET last_heartbeat = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (agent_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    # ========== Dashboard ==========
    
    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM v_dashboard_stats')
        row = cursor.fetchone()
        if row:
            return {
                'total_agents': row[0],
                'active_agents': row[1],
                'idle_agents': row[2],
                'blocked_agents': row[3],
                'total_projects': row[4],
                'active_projects': row[5],
                'total_tasks': row[6],
                'todo_tasks': row[7],
                'in_progress_tasks': row[8],
                'completed_tasks': row[9],
                'blocked_tasks': row[10],
                'avg_progress': row[11],
                'due_today': row[12],
                'overdue_tasks': row[13]
            }
        return {}
    
    def get_project_status(self) -> List[Dict]:
        """Get all projects with status"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM v_project_status ORDER BY progress_pct DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== Reports ==========
    
    def generate_daily_report(self) -> str:
        """Generate daily report"""
        stats = self.get_dashboard_stats()
        tasks_done_today = self._get_tasks_completed_today()
        
        report = f"""
# AI Team Daily Report - {datetime.now().strftime('%Y-%m-%d')}

## 📊 Summary
- Total Tasks: {stats.get('total_tasks', 0)}
- Completed Today: {len(tasks_done_today)}
- In Progress: {stats.get('in_progress_tasks', 0)}
- Blocked: {stats.get('blocked_tasks', 0)}
- Active Agents: {stats.get('active_agents', 0)}

## ✅ Tasks Completed Today
"""
        for task in tasks_done_today:
            report += f"- {task['id']}: {task['title']} (by {task['assignee']})\n"
        
        report += "\n## 🔄 In Progress\n"
        in_progress = self.get_tasks(status='in_progress')
        for task in in_progress[:5]:
            report += f"- {task['id']}: {task['title']} ({task['progress']}%) - {task['assignee_name']}\n"
        
        report += "\n## 🚧 Blocked\n"
        blocked = self.get_tasks(status='blocked')
        for task in blocked:
            report += f"- {task['id']}: {task['title']} - {task['assignee_name']}\n"
        
        return report
    
    # ========== Helper Methods ==========
    
    @staticmethod
    def format_duration(minutes: int) -> str:
        """Format duration in human-readable format (e.g., '2h 30m', '45m', '1d 2h')"""
        if minutes is None or minutes < 0:
            return "-"
        
        days = minutes // 1440
        hours = (minutes % 1440) // 60
        mins = minutes % 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if mins > 0 or (days == 0 and hours == 0):
            parts.append(f"{mins}m")
        
        return " ".join(parts) if parts else "0m"
    
    def get_task_duration(self, task_id: str) -> dict:
        """Get task duration info"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT started_at, completed_at, actual_duration_minutes
            FROM tasks WHERE id = ?
        ''', (task_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return {
            'started_at': row[0],
            'completed_at': row[1],
            'actual_duration_minutes': row[2],
            'duration_formatted': self.format_duration(row[2])
        }
    
    def _get_next_task_number(self) -> int:
        """Get next task number for today"""
        cursor = self.conn.cursor()
        today = datetime.now().strftime('%Y%m%d')
        cursor.execute("""
            SELECT COUNT(*) FROM tasks 
            WHERE id LIKE ?
        """, (f'T-{today}-%',))
        return cursor.fetchone()[0] + 1
    
    def _get_tasks_completed_today(self) -> List[Dict]:
        """Get tasks completed today"""
        cursor = self.conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT t.id, t.title, a.name as assignee,
                   t.actual_duration_minutes
            FROM tasks t
            JOIN agents a ON t.assignee_id = a.id
            WHERE DATE(t.completed_at) = ?
        ''', (today,))
        return [dict(row) for row in cursor.fetchall()]
    
    def recalculate_durations(self) -> int:
        """Recalculate actual_duration_minutes for all completed tasks that don't have it set"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE tasks 
            SET actual_duration_minutes = ROUND((strftime('%s', completed_at) - strftime('%s', started_at)) / 60)
            WHERE status = 'done' 
              AND completed_at IS NOT NULL 
              AND started_at IS NOT NULL
              AND actual_duration_minutes IS NULL
        ''')
        self.conn.commit()
        return cursor.rowcount


def main():
    parser = argparse.ArgumentParser(description='AI Team Database Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Task commands
    task_parser = subparsers.add_parser('task', help='Task management')
    task_sub = task_parser.add_subparsers(dest='task_action')
    
    create = task_sub.add_parser('create', help='Create new task')
    create.add_argument('title', help='Task title')
    create.add_argument('--desc', default='', help='Task description')
    create.add_argument('--assign', help='Assign to agent')
    create.add_argument('--project', help='Project ID')
    create.add_argument('--priority', choices=['critical', 'high', 'normal', 'low'], 
                       default='normal', help='Task priority')
    create.add_argument('--due', help='Due date (YYYY-MM-DD)')
    
    assign = task_sub.add_parser('assign', help='Assign task')
    assign.add_argument('task_id', help='Task ID')
    assign.add_argument('agent_id', help='Agent ID')
    
    start = task_sub.add_parser('start', help='Start task')
    start.add_argument('task_id', help='Task ID')
    
    progress = task_sub.add_parser('progress', help='Update progress')
    progress.add_argument('task_id', help='Task ID')
    progress.add_argument('percent', type=int, help='Progress percentage')
    progress.add_argument('--notes', default='', help='Progress notes')
    
    done = task_sub.add_parser('done', help='Complete task')
    done.add_argument('task_id', help='Task ID')
    
    review = task_sub.add_parser('review', help='Send task to review')
    review.add_argument('task_id', help='Task ID')
    
    block = task_sub.add_parser('block', help='Block task')
    block.add_argument('task_id', help='Task ID')
    block.add_argument('reason', help='Block reason')
    
    unblock = task_sub.add_parser('unblock', help='Unblock and resume task')
    unblock.add_argument('task_id', help='Task ID')
    unblock.add_argument('--agent', help='Agent ID resuming the task')
    
    list_tasks = task_sub.add_parser('list', help='List tasks')
    list_tasks.add_argument('--status', choices=['todo', 'in_progress', 'done', 'blocked'],
                           help='Filter by status')
    list_tasks.add_argument('--agent', help='Filter by agent')
    
    # Agent commands
    agent_parser = subparsers.add_parser('agent', help='Agent management')
    agent_sub = agent_parser.add_subparsers(dest='agent_action')
    
    list_agents = agent_sub.add_parser('list', help='List agents')
    list_agents.add_argument('--status', choices=['idle', 'active', 'blocked'],
                            help='Filter by status')
    
    heartbeat = agent_sub.add_parser('heartbeat', help='Update agent heartbeat')
    heartbeat.add_argument('agent_id', help='Agent ID')
    
    # Dashboard commands
    dash_parser = subparsers.add_parser('dashboard', help='Dashboard')
    dash_parser.add_argument('--export', choices=['json', 'markdown'],
                            help='Export format')
    
    # Report commands
    report_parser = subparsers.add_parser('report', help='Generate reports')
    report_parser.add_argument('--daily', action='store_true', help='Daily report')
    
    args = parser.parse_args()
    
    with AITeamDB() as db:
        if args.command == 'task':
            if args.task_action == 'create':
                task_id = db.create_task(
                    title=args.title,
                    description=args.desc,
                    assignee_id=args.assign,
                    project_id=args.project,
                    priority=args.priority,
                    due_date=args.due
                )
                print(f"✅ Task created: {task_id}")
                
            elif args.task_action == 'assign':
                if db.assign_task(args.task_id, args.agent_id):
                    print(f"✅ Task {args.task_id} assigned to {args.agent_id}")
                    
            elif args.task_action == 'start':
                if db.start_task(args.task_id):
                    print(f"✅ Task {args.task_id} started")
            
            elif args.task_action == 'review':
                if db.send_to_review(args.task_id):
                    print(f"✅ Task {args.task_id} sent to review")
                    
            elif args.task_action == 'progress':
                if db.update_progress(args.task_id, args.percent, args.notes):
                    print(f"✅ Task {args.task_id} progress: {args.percent}%")
                    
            elif args.task_action == 'done':
                if db.complete_task(args.task_id):
                    print(f"✅ Task {args.task_id} completed")
                    
            elif args.task_action == 'block':
                if db.block_task(args.task_id, args.reason):
                    print(f"⚠️ Task {args.task_id} blocked: {args.reason}")
            
            elif args.task_action == 'unblock':
                if db.unblock_task(args.task_id, args.agent):
                    print(f"✅ Task {args.task_id} unblocked and resumed")
                    
            elif args.task_action == 'list':
                tasks = db.get_tasks(status=args.status, assignee=args.agent)
                print(f"\n📋 Tasks ({len(tasks)} total):\n")
                for t in tasks:
                    status_emoji = {
                        'todo': '⬜', 'in_progress': '🔄',
                        'done': '✅', 'blocked': '🚧'
                    }.get(t['status'], '⬜')
                    print(f"{status_emoji} {t['id']} | {t['title'][:40]}...")
                    print(f"   Status: {t['status']} | Assignee: {t['assignee_name'] or 'Unassigned'}")
                    if t['progress'] > 0:
                        print(f"   Progress: {t['progress']}%")
                    print()
                    
        elif args.command == 'agent':
            if args.agent_action == 'list':
                agents = db.get_agents(status=args.status)
                print(f"\n🤖 Agents ({len(agents)} total):\n")
                for a in agents:
                    status_emoji = {
                        'idle': '⚪', 'active': '🟢',
                        'blocked': '🔴', 'offline': '⚫'
                    }.get(a['status'], '⚪')
                    print(f"{status_emoji} {a['name']} ({a['role']})")
                    print(f"   Status: {a['status']}")
                    print(f"   Tasks: {a['active_tasks']} active, {a['total_tasks_completed']} completed")
                    if a['avg_progress']:
                        print(f"   Avg Progress: {a['avg_progress']:.1f}%")
                    print()
                    
            elif args.agent_action == 'heartbeat':
                if db.update_agent_heartbeat(args.agent_id):
                    print(f"💓 Heartbeat updated for {args.agent_id}")
                    
        elif args.command == 'dashboard':
            stats = db.get_dashboard_stats()
            print("\n📊 Dashboard Stats:\n")
            print(f"Total Tasks: {stats.get('total_tasks', stats.get(6, 0))}")
            print(f"  - Todo: {stats.get('todo_tasks', stats.get(7, 0))}")
            print(f"  - In Progress: {stats.get('in_progress_tasks', stats.get(8, 0))}")
            print(f"  - Done: {stats.get('completed_tasks', stats.get(9, 0))}")
            print(f"  - Blocked: {stats.get('blocked_tasks', stats.get(10, 0))}")
            print(f"\nAgents:")
            print(f"  - Total: {stats.get('total_agents', stats.get(0, 0))}")
            print(f"  - Active: {stats.get('active_agents', stats.get(1, 0))}")
            print(f"  - Idle: {stats.get('idle_agents', stats.get(2, 0))}")
            print(f"  - Blocked: {stats.get('blocked_agents', stats.get(3, 0))}")
            print(f"\nDue:")
            print(f"  - Due Today: {stats.get('due_today', stats.get(12, 0))}")
            print(f"  - Overdue: {stats.get('overdue_tasks', stats.get(13, 0))}")
            
        elif args.command == 'report':
            if args.daily:
                report = db.generate_daily_report()
                print(report)
        else:
            parser.print_help()


if __name__ == '__main__':
    main()
