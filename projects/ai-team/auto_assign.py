#!/usr/bin/env python3
"""
AI Team Auto-Assign
Automatically assign idle agents to todo tasks
"""

import os
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

os.environ['TZ'] = 'Asia/Bangkok'

DB_PATH = Path(__file__).parent / "team.db"
TELEGRAM_CHANNEL = "1268858185"

# Role matching for task assignment
ROLE_MATCH = {
    'dev': ['dev', 'solo-dev'],
    'frontend': ['dev', 'ux-designer'],
    'backend': ['dev', 'architect'],
    'database': ['architect', 'dev'],
    'api': ['dev', 'architect'],
    'ui': ['ux-designer'],
    'ux': ['ux-designer'],
    'test': ['qa'],
    'qa': ['qa'],
    'doc': ['tech-writer'],
    'document': ['tech-writer'],
    'design': ['ux-designer'],
    'plan': ['pm', 'analyst'],
    'analyze': ['analyst'],
    'review': ['qa'],
}

class AutoAssign:
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

    def get_idle_agents(self) -> List[Dict]:
        """Get list of idle agents with their roles"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, role
            FROM agents
            WHERE status = 'idle'
            AND (current_task_id IS NULL OR current_task_id = '')
            ORDER BY total_tasks_completed ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def get_unassigned_todo_tasks(self) -> List[Dict]:
        """Get todo tasks without assignee"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT t.id, t.title, t.description, t.priority, t.project_id
            FROM tasks t
            WHERE t.status = 'todo'
            AND (t.assignee_id IS NULL OR t.assignee_id = '')
            ORDER BY 
                CASE t.priority 
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'normal' THEN 3
                    WHEN 'low' THEN 4
                END,
                t.created_at ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def find_best_agent(self, task: Dict, agents: List[Dict]) -> Optional[Dict]:
        """Find best matching agent for a task based on keywords"""
        title_lower = task['title'].lower()
        desc_lower = (task.get('description') or '').lower()
        task_text = title_lower + ' ' + desc_lower
        
        # Score each agent
        best_agent = None
        best_score = -1
        
        for agent in agents:
            score = 0
            agent_role = agent['role'].lower()
            
            # Check role matches
            for keyword, matching_roles in ROLE_MATCH.items():
                if keyword in task_text:
                    if agent['id'] in matching_roles or agent_role in matching_roles:
                        score += 10
            
            # Prefer agents with fewer completed tasks (load balancing)
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM tasks 
                WHERE assignee_id = ? AND status = 'in_progress'
            ''', (agent['id'],))
            active_count = cursor.fetchone()[0]
            score -= active_count * 5  # Penalty for busy agents
            
            if score > best_score:
                best_score = score
                best_agent = agent
        
        return best_agent

    def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign task to agent"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE tasks 
                SET assignee_id = ?, status = 'todo', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (agent_id, task_id))
            
            cursor.execute('''
                UPDATE agents 
                SET total_tasks_assigned = total_tasks_assigned + 1,
                    current_task_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (task_id, agent_id))
            
            cursor.execute('''
                INSERT INTO task_history (task_id, agent_id, action, notes)
                VALUES (?, ?, 'auto_assigned', 'Auto-assigned by system')
            ''', (task_id, agent_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[Error] Failed to assign task: {e}")
            return False

    def spawn_worker(self, task: Dict, agent: Dict) -> bool:
        """Spawn subagent to work on task"""
        try:
            # Update agent status to active
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE agents 
                SET status = 'active', last_heartbeat = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (agent['id'],))
            self.conn.commit()
            
            print(f"  🚀 Spawned {agent['name']} to work on {task['id']}")
            return True
        except Exception as e:
            print(f"[Error] Failed to spawn worker: {e}")
            return False

    def auto_start_assigned_tasks(self) -> int:
        """Start tasks that are assigned to idle agents"""
        cursor = self.conn.cursor()
        
        # Find todo tasks that have assignee but agent is idle
        cursor.execute('''
            SELECT t.id, t.title, t.assignee_id, a.name as agent_name
            FROM tasks t
            JOIN agents a ON t.assignee_id = a.id
            WHERE t.status = 'todo'
            AND t.assignee_id IS NOT NULL
            AND a.status = 'idle'
        ''')
        
        tasks_to_start = [dict(row) for row in cursor.fetchall()]
        started_count = 0
        
        for task in tasks_to_start:
            print(f"   🚀 Starting {task['id']} (assigned to {task['agent_name']})")
            
            try:
                # Update task to in_progress
                cursor.execute('''
                    UPDATE tasks 
                    SET status = 'in_progress', 
                        started_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (task['id'],))
                
                # Update agent to active
                cursor.execute('''
                    UPDATE agents 
                    SET status = 'active',
                        current_task_id = ?,
                        last_heartbeat = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (task['id'], task['assignee_id']))
                
                # Log history
                cursor.execute('''
                    INSERT INTO task_history (task_id, agent_id, action, notes)
                    VALUES (?, ?, 'started', 'Auto-started by system')
                ''', (task['id'], task['assignee_id']))
                
                self.conn.commit()
                started_count += 1
                
            except Exception as e:
                print(f"   [Error] Failed to start {task['id']}: {e}")
        
        if started_count == 0:
            print("   ℹ️ No tasks to start")
        
        return started_count

    def send_notification(self, message: str) -> bool:
        """Send notification to Telegram"""
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
            print(f"[Notification Error] {e}")
            return False

    def run(self) -> Dict:
        """Main auto-assign logic"""
        print("🤖 AI Team Auto-Assign Starting...")
        print("=" * 50)
        
        # Get available resources
        idle_agents = self.get_idle_agents()
        todo_tasks = self.get_unassigned_todo_tasks()
        
        print(f"\n📊 Status:")
        print(f"   Idle agents: {len(idle_agents)}")
        print(f"   Unassigned tasks: {len(todo_tasks)}")
        
        if not idle_agents:
            print("\n⚠️ No idle agents available")
            # Still try to start assigned tasks
            started_count = self.auto_start_assigned_tasks()
            return {'assigned': 0, 'started': started_count, 'agents': 0, 'tasks': len(todo_tasks)}
        
        # Assign new tasks
        assigned_count = 0
        assigned_pairs = []
        
        for task in todo_tasks:
            if not idle_agents:
                break
            
            best_agent = self.find_best_agent(task, idle_agents)
            if not best_agent:
                best_agent = idle_agents[0]  # Fallback to first available
            
            print(f"\n📝 Task: {task['id']} - {task['title']}")
            print(f"   → Assigned to: {best_agent['name']} ({best_agent['role']})")
            
            if self.assign_task(task['id'], best_agent['id']):
                if self.spawn_worker(task, best_agent):
                    assigned_count += 1
                    assigned_pairs.append({
                        'task': task['id'],
                        'agent': best_agent['name']
                    })
                    # Remove assigned agent from pool
                    idle_agents = [a for a in idle_agents if a['id'] != best_agent['id']]
        
        # Also start tasks that are assigned to idle agents but not started
        print("\n🚀 Checking for assigned tasks to start...")
        started_count = self.auto_start_assigned_tasks()
        
        total_actions = assigned_count + started_count
        
        # Send summary notification
        if total_actions > 0:
            message = f"🤖 *Auto-Task Manager*\n\n"
            if assigned_count > 0:
                message += f"*Assigned:* {assigned_count} tasks\n"
                for pair in assigned_pairs:
                    message += f"• {pair['task']} → {pair['agent']}\n"
            if started_count > 0:
                message += f"\n*Started:* {started_count} tasks\n"
            message += f"\n⏰ {datetime.now().strftime('%H:%M')}"
            self.send_notification(message)
            print(f"\n📤 Notification sent")
        
        print("\n" + "=" * 50)
        print(f"✅ Complete: {assigned_count} assigned, {started_count} started")
        
        return {
            'assigned': assigned_count,
            'started': started_count,
            'agents': len(idle_agents),
            'tasks': len(todo_tasks)
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='AI Team Auto-Assign')
    parser.add_argument('--run', action='store_true', help='Run auto-assign once')
    args = parser.parse_args()
    
    with AutoAssign() as assigner:
        if args.run or True:  # Default to run
            result = assigner.run()
            exit(0 if result['assigned'] >= 0 else 1)


if __name__ == '__main__':
    main()
