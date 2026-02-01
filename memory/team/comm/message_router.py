#!/usr/bin/env python3
"""
AI Team Message Router
Central hub for agent-to-agent communication with Telegram notifications
"""

import sqlite3
import uuid
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import sys

# Database paths
TEAM_DB = Path(__file__).parent.parent / "team.db"
MESSAGES_DB = Path(__file__).parent.parent / "messages.db"


class MessageRouter:
    """Route messages between agents and notify Telegram"""
    
    def __init__(self):
        self.messages_db = MESSAGES_DB
        self.team_db = TEAM_DB
        
    def _get_db(self, db_path: Path):
        """Get database connection"""
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def request_help(
        self,
        from_agent: str,
        issue: str,
        context_task: str = None,
        urgency: str = "normal",
        suggested_helpers: List[str] = None
    ) -> str:
        """
        Agent requests help - notifies helpers and Telegram
        """
        escalation_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        conversation_id = f"CONV-{uuid.uuid4().hex[:8].upper()}"
        
        conn = self._get_db(self.messages_db)
        cursor = conn.cursor()
        
        try:
            # 1. Create escalation record
            cursor.execute('''
                INSERT INTO escalations 
                (escalation_id, task_id, from_agent, issue_type, description, priority)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (escalation_id, context_task, from_agent, 'technical', issue, urgency))
            
            # 2. Create conversation record
            cursor.execute('''
                INSERT INTO conversations
                (conversation_id, from_agent, message_type, content, context_task_id, urgency)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (conversation_id, from_agent, 'help', issue, context_task, urgency))
            
            conn.commit()
            
            # 3. Find helpers if not specified
            if not suggested_helpers:
                suggested_helpers = self._find_best_helpers(issue)
            
            # 4. Send to helpers (simulate)
            helper_notifications = []
            for helper in suggested_helpers:
                msg = f"🆘 Help request from {from_agent}: {issue[:50]}..."
                helper_notifications.append(f"[TO {helper.upper()}] {msg}")
            
            # 5. Create Telegram notification
            telegram_msg = self._format_telegram_help(
                from_agent=from_agent,
                escalation_id=escalation_id,
                task_id=context_task,
                issue=issue,
                urgency=urgency,
                helpers=suggested_helpers
            )
            
            # Store notification
            notif_id = f"NOTIF-{uuid.uuid4().hex[:8]}"
            cursor.execute('''
                INSERT INTO notifications (notification_id, conversation_id, content)
                VALUES (?, ?, ?)
            ''', (notif_id, conversation_id, telegram_msg))
            conn.commit()
            
            return {
                'escalation_id': escalation_id,
                'conversation_id': conversation_id,
                'helpers_notified': suggested_helpers,
                'telegram_notification': telegram_msg,
                'helper_messages': helper_notifications
            }
            
        finally:
            conn.close()
    
    def reply_to_help(
        self,
        from_agent: str,
        to_agent: str,
        reply_message: str,
        escalation_id: str,
        context_task: str = None
    ) -> Dict:
        """
        Agent replies to help request - notifies requester and Telegram
        """
        conversation_id = f"CONV-{uuid.uuid4().hex[:8].upper()}"
        
        conn = self._get_db(self.messages_db)
        cursor = conn.cursor()
        
        try:
            # Get original escalation details
            cursor.execute('''
                SELECT from_agent, description FROM escalations WHERE escalation_id = ?
            ''', (escalation_id,))
            row = cursor.fetchone()
            
            if not row:
                return {'error': f'Escalation {escalation_id} not found'}
            
            original_requester = row[0]
            original_issue = row[1]
            
            # 1. Create reply conversation
            cursor.execute('''
                INSERT INTO conversations
                (conversation_id, from_agent, to_agent, message_type, content, context_task_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (conversation_id, from_agent, to_agent, 'answer', reply_message, context_task))
            
            # 2. Update escalation with helper
            cursor.execute('''
                UPDATE escalations 
                SET assigned_helper = ?, status = 'in_progress'
                WHERE escalation_id = ?
            ''', (from_agent, escalation_id))
            
            conn.commit()
            
            # 3. Create Telegram notification
            telegram_msg = self._format_telegram_reply(
                from_agent=from_agent,
                to_agent=to_agent,
                escalation_id=escalation_id,
                task_id=context_task,
                reply=reply_message,
                original_issue=original_issue
            )
            
            # Store notification
            notif_id = f"NOTIF-{uuid.uuid4().hex[:8]}"
            cursor.execute('''
                INSERT INTO notifications (notification_id, conversation_id, content)
                VALUES (?, ?, ?)
            ''', (notif_id, conversation_id, telegram_msg))
            conn.commit()
            
            return {
                'conversation_id': conversation_id,
                'to_agent': to_agent,
                'telegram_notification': telegram_msg
            }
            
        finally:
            conn.close()
    
    def resolve_escalation(
        self,
        escalation_id: str,
        resolution_notes: str,
        resolved_by: str
    ) -> Dict:
        """
        Mark escalation as resolved - notifies all involved and Telegram
        """
        conn = self._get_db(self.messages_db)
        cursor = conn.cursor()
        
        try:
            # Get escalation details
            cursor.execute('''
                SELECT from_agent, assigned_helper, task_id, description, created_at
                FROM escalations WHERE escalation_id = ?
            ''', (escalation_id,))
            row = cursor.fetchone()
            
            if not row:
                return {'error': f'Escalation {escalation_id} not found'}
            
            from_agent, helper, task_id, issue, created_at = row
            
            # Calculate resolution time
            created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            resolution_time = datetime.now() - created_dt
            minutes_taken = int(resolution_time.total_seconds() / 60)
            
            # Update escalation
            cursor.execute('''
                UPDATE escalations 
                SET status = 'resolved', 
                    resolved_at = CURRENT_TIMESTAMP,
                    resolution_notes = ?
                WHERE escalation_id = ?
            ''', (resolution_notes, escalation_id))
            conn.commit()
            
            # Create Telegram notification
            telegram_msg = self._format_telegram_resolved(
                escalation_id=escalation_id,
                task_id=task_id,
                issue=issue,
                resolved_by=resolved_by,
                resolution_notes=resolution_notes,
                minutes_taken=minutes_taken
            )
            
            # Store notification
            notif_id = f"NOTIF-{uuid.uuid4().hex[:8]}"
            cursor.execute('''
                INSERT INTO notifications (notification_id, conversation_id, content)
                VALUES (?, ?, ?)
            ''', (notif_id, None, telegram_msg))
            conn.commit()
            
            involved = list(set([a for a in [from_agent, helper, resolved_by] if a]))
            
            return {
                'escalation_id': escalation_id,
                'status': 'resolved',
                'resolution_time_minutes': minutes_taken,
                'involved_agents': involved,
                'telegram_notification': telegram_msg
            }
            
        finally:
            conn.close()
    
    def broadcast_message(
        self,
        from_agent: str,
        message: str,
        urgency: str = "normal"
    ) -> Dict:
        """
        Broadcast message to all agents
        """
        conversation_id = f"CONV-{uuid.uuid4().hex[:8].upper()}"
        
        conn = self._get_db(self.messages_db)
        cursor = conn.cursor()
        
        try:
            # Create broadcast conversation
            cursor.execute('''
                INSERT INTO conversations
                (conversation_id, from_agent, message_type, content, urgency)
                VALUES (?, ?, ?, ?, ?)
            ''', (conversation_id, from_agent, 'broadcast', message, urgency))
            conn.commit()
            
            # Get all agents
            team_conn = self._get_db(self.team_db)
            team_cursor = team_conn.cursor()
            team_cursor.execute('SELECT id, name FROM agents')
            all_agents = [dict(row) for row in team_cursor.fetchall()]
            team_conn.close()
            
            # Create Telegram notification
            telegram_msg = self._format_telegram_broadcast(
                from_agent=from_agent,
                message=message,
                urgency=urgency
            )
            
            # Store notification
            notif_id = f"NOTIF-{uuid.uuid4().hex[:8]}"
            cursor.execute('''
                INSERT INTO notifications (notification_id, conversation_id, content)
                VALUES (?, ?, ?)
            ''', (notif_id, conversation_id, telegram_msg))
            conn.commit()
            
            return {
                'conversation_id': conversation_id,
                'recipients': len(all_agents),
                'telegram_notification': telegram_msg
            }
            
        finally:
            conn.close()
    
    def _find_best_helpers(self, issue: str) -> List[str]:
        """Find best agents to help based on issue keywords"""
        issue_lower = issue.lower()
        
        keywords = {
            'database': ['architect', 'dev'],
            'sql': ['architect', 'dev'],
            'schema': ['architect'],
            'ui': ['ux-designer', 'dev'],
            'css': ['ux-designer', 'dev'],
            'design': ['ux-designer'],
            'layout': ['ux-designer'],
            'test': ['qa', 'solo-dev'],
            'bug': ['qa', 'solo-dev', 'architect'],
            'error': ['qa', 'solo-dev', 'architect'],
            'fail': ['qa', 'solo-dev'],
            'requirement': ['pm', 'analyst'],
            'spec': ['pm', 'analyst'],
            'feature': ['pm', 'analyst'],
            'auth': ['architect', 'dev'],
            'security': ['architect', 'qa'],
            'performance': ['architect', 'dev'],
        }
        
        matched_helpers = set()
        for keyword, helpers in keywords.items():
            if keyword in issue_lower:
                matched_helpers.update(helpers)
        
        return list(matched_helpers) if matched_helpers else ['architect', 'solo-dev']
    
    def _format_telegram_help(self, from_agent, escalation_id, task_id, issue, urgency, helpers):
        """Format help request for Telegram"""
        urgency_emoji = {'critical': '🔴', 'high': '🟠', 'normal': '🟡', 'low': '🔵'}.get(urgency, '⚪')
        
        return f"""{urgency_emoji} HELP REQUEST

From: {from_agent.upper()}
Escalation: {escalation_id}
Task: {task_id or 'N/A'}
Urgency: {urgency.upper()}

Issue:
{issue}

Notified: {', '.join(helpers)}

[View Details] [Assign Helper] [Mark Resolved]
"""
    
    def _format_telegram_reply(self, from_agent, to_agent, escalation_id, task_id, reply, original_issue):
        """Format reply for Telegram"""
        return f"""💬 AGENT REPLY

{from_agent.upper()} → {to_agent.upper()}
Escalation: {escalation_id}
Task: {task_id or 'N/A'}

Original Issue:
{original_issue[:100]}...

Reply:
{reply}

[View Thread] [Reply] [Mark Resolved]
"""
    
    def _format_telegram_resolved(self, escalation_id, task_id, issue, resolved_by, resolution_notes, minutes_taken):
        """Format resolution for Telegram"""
        hours = minutes_taken // 60
        mins = minutes_taken % 60
        time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        
        return f"""✅ ISSUE RESOLVED

Escalation: {escalation_id}
Task: {task_id or 'N/A'}

Issue:
{issue[:100]}...

Resolved by: {resolved_by.upper()}
Time to resolve: {time_str}

Solution:
{resolution_notes}

[View Details] [Close Thread]
"""
    
    def _format_telegram_broadcast(self, from_agent, message, urgency):
        """Format broadcast for Telegram"""
        return f"""📢 BROADCAST from {from_agent.upper()}

{message}

[Acknowledge] [View All]
"""
    
    def get_conversations(self, agent_id: str = None, status: str = None) -> List[Dict]:
        """Get conversations with optional filters"""
        conn = self._get_db(self.messages_db)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM conversations WHERE 1=1'
        params = []
        
        if agent_id:
            query += ' AND (from_agent = ? OR to_agent = ? OR to_agent IS NULL)'
            params.extend([agent_id, agent_id])
        if status:
            query += ' AND status = ?'
            params.append(status)
            
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_escalations(self, status: str = None) -> List[Dict]:
        """Get escalations with optional filter"""
        conn = self._get_db(self.messages_db)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT * FROM escalations WHERE status = ? ORDER BY created_at DESC', (status,))
        else:
            cursor.execute('SELECT * FROM escalations ORDER BY created_at DESC')
            
        return [dict(row) for row in cursor.fetchall()]


def main():
    parser = argparse.ArgumentParser(description='AI Team Message Router')
    parser.add_argument('action', choices=['help', 'reply', 'resolve', 'broadcast', 'list'])
    parser.add_argument('--from', dest='from_agent', help='Source agent')
    parser.add_argument('--to', dest='to_agent', help='Target agent')
    parser.add_argument('--message', '-m', help='Message content')
    parser.add_argument('--task', '-t', help='Task ID')
    parser.add_argument('--escalation', '-e', help='Escalation ID')
    parser.add_argument('--urgency', '-u', default='normal', choices=['low', 'normal', 'high', 'critical'])
    parser.add_argument('--helpers', help='Comma-separated helper list')
    
    args = parser.parse_args()
    
    router = MessageRouter()
    
    if args.action == 'help':
        if not args.from_agent or not args.message:
            print("❌ Error: --from and --message required")
            return
        
        helpers = args.helpers.split(',') if args.helpers else None
        result = router.request_help(
            from_agent=args.from_agent,
            issue=args.message,
            context_task=args.task,
            urgency=args.urgency,
            suggested_helpers=helpers
        )
        
        print(f"\n🆘 HELP REQUEST CREATED")
        print(f"Escalation ID: {result['escalation_id']}")
        print(f"Helpers notified: {', '.join(result['helpers_notified'])}")
        print(f"\n📱 TELEGRAM NOTIFICATION:\n{result['telegram_notification']}")
        
    elif args.action == 'reply':
        if not all([args.from_agent, args.to_agent, args.message, args.escalation]):
            print("❌ Error: --from, --to, --message, and --escalation required")
            return
        
        result = router.reply_to_help(
            from_agent=args.from_agent,
            to_agent=args.to_agent,
            reply_message=args.message,
            escalation_id=args.escalation,
            context_task=args.task
        )
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"\n💬 REPLY SENT")
            print(f"To: {result['to_agent']}")
            print(f"\n📱 TELEGRAM NOTIFICATION:\n{result['telegram_notification']}")
            
    elif args.action == 'resolve':
        if not all([args.escalation, args.message, args.from_agent]):
            print("❌ Error: --escalation, --message, and --from required")
            return
        
        result = router.resolve_escalation(
            escalation_id=args.escalation,
            resolution_notes=args.message,
            resolved_by=args.from_agent
        )
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"\n✅ ESCALATION RESOLVED")
            print(f"ID: {result['escalation_id']}")
            print(f"Resolution time: {result['resolution_time_minutes']} minutes")
            print(f"\n📱 TELEGRAM NOTIFICATION:\n{result['telegram_notification']}")
            
    elif args.action == 'broadcast':
        if not args.from_agent or not args.message:
            print("❌ Error: --from and --message required")
            return
        
        result = router.broadcast_message(
            from_agent=args.from_agent,
            message=args.message,
            urgency=args.urgency
        )
        
        print(f"\n📢 BROADCAST SENT")
        print(f"Recipients: {result['recipients']} agents")
        print(f"\n📱 TELEGRAM NOTIFICATION:\n{result['telegram_notification']}")
        
    elif args.action == 'list':
        print("\n📨 RECENT CONVERSATIONS:\n")
        conversations = router.get_conversations(agent_id=args.from_agent)
        for c in conversations[:10]:
            to_str = f"→ {c['to_agent']}" if c['to_agent'] else "(broadcast)"
            print(f"[{c['created_at'][:16]}] {c['from_agent']} {to_str}")
            print(f"  Type: {c['message_type']} | Status: {c['status']}")
            print(f"  {c['content'][:60]}...\n")


if __name__ == '__main__':
    main()
