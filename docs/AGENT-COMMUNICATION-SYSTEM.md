# 🤖 AI Team - Agent Communication System

**Version:** 1.0.0  
**Created:** 2026-02-01  
**Status:** Design Proposal

---

## 🎯 เป้าหมาย

1. Agents คุยกันได้เมื่อมีปัญหา
2. ทุกการสื่อสารส่งมาที่ Telegram (ผู้ใช้รับรู้)
3. ระบบช่วยเหลือ/แก้ไขปัญหาร่วมกัน

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         COMMUNICATION FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

Scenario: Dev (Amelia) ติดปัญหา ต้องการความช่วยเหลือ

┌─────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────┐
│  💻 Dev │────▶│ 📨 MESSAGE   │────▶│ 🎛️         │────▶│  👤     │
│ (Amelia)│     │   QUEUE      │     │ Orchestrator │     │  User   │
│         │     │   (SQLite)   │     │  (Master)    │     │(Telegram│
└────┬────┘     └──────────────┘     └──────┬───────┘     └─────────┘
     │                                      │
     │ "Help needed: Bug in auth"           │ Forward to Telegram
     │                                      │
     ▼                                      ▼
┌──────────────┐                    ┌──────────────┐
│  🏗️          │◀─── Auto notify ───│  🏃          │
│  Architect   │                    │  Scrum Master│
│  (Winston)   │                    │   (Bob)      │
└──────────────┘                    └──────────────┘
     │
     ▼ Reply
"Check JWT config"
     │
     └──────────────────────────────────────▶ Telegram
                                              "Winston suggests: Check JWT"
```

---

## 📁 โครงสร้างระบบ

```
~/clawd/memory/team/
├── team.db                    # หลัก: tasks, agents
├── messages.db               # ใหม่: ระบบสื่อสาร
│   ├── conversations         # บทสนทนา
│   ├── notifications         # แจ้งเตือน
│   └── escalations          # ปัญหาที่ต้องแก้
├── dashboard.html
├── team_db.py
└── comm/
    ├── message_router.py    # ระบบกลางส่งข้อความ
    ├── notification.py      # แจ้งเตือน Telegram
    └── escalation.py        # ระบบช่วยเหลือ
```

---

## 🗄️ Database Schema (messages.db)

```sql
-- บทสนทนาระหว่าง Agents
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,      -- UUID ของบทสนทนา
    from_agent TEXT NOT NULL,           -- Agent ที่ส่ง
    to_agent TEXT,                      -- Agent ปลายทาง (NULL = broadcast)
    message_type TEXT,                  -- help, update, question, answer
    content TEXT NOT NULL,
    context_task_id TEXT,               -- เกี่ยวข้องกับงานไหน
    urgency TEXT DEFAULT 'normal',      -- low, normal, high, critical
    status TEXT DEFAULT 'unread',       -- unread, read, resolved
    parent_message_id INTEGER,          -- Reply ข้อความไหน
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME,
    FOREIGN KEY (parent_message_id) REFERENCES conversations(id)
);

-- แจ้งเตือนที่ส่งไป Telegram
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id TEXT NOT NULL,
    conversation_id TEXT,
    channel TEXT DEFAULT 'telegram',    -- telegram, web, both
    content TEXT NOT NULL,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    delivered BOOLEAN DEFAULT FALSE,
    delivered_at DATETIME,
    read_by_user BOOLEAN DEFAULT FALSE,
    read_at DATETIME
);

-- ปัญหาที่ต้องการความช่วยเหลือ
CREATE TABLE escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    escalation_id TEXT NOT NULL,
    task_id TEXT,
    from_agent TEXT NOT NULL,
    issue_type TEXT,                    -- technical, requirement, blocked
    description TEXT NOT NULL,
    suggested_solution TEXT,
    assigned_helper TEXT,               -- Agent ที่ได้รับมอบหมายให้ช่วย
    status TEXT DEFAULT 'open',         -- open, assigned, in_progress, resolved
    priority TEXT DEFAULT 'normal',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    resolution_notes TEXT
);

-- Agent subscriptions (ใครต้องการรับข้อความประเภทไหน)
CREATE TABLE agent_subscriptions (
    agent_id TEXT NOT NULL,
    message_type TEXT NOT NULL,         -- help, update, all
    urgency_min TEXT DEFAULT 'normal',  -- รับตั้งแต่ urgency ไหนขึ้นไป
    PRIMARY KEY (agent_id, message_type)
);

-- Views
CREATE VIEW v_unread_messages AS
SELECT 
    c.*,
    t.title as task_title,
    CASE 
        WHEN julianday('now') - julianday(c.created_at) > 1 THEN 'overdue'
        WHEN julianday('now') - julianday(c.created_at) > 0.5 THEN 'urgent'
        ELSE 'normal'
    END as response_urgency
FROM conversations c
LEFT JOIN tasks t ON c.context_task_id = t.id
WHERE c.status = 'unread';

CREATE VIEW v_active_escalations AS
SELECT 
    e.*,
    a.name as from_agent_name,
    h.name as helper_name,
    t.title as task_title,
    julianday('now') - julianday(e.created_at) as hours_open
FROM escalations e
JOIN agents a ON e.from_agent = a.id
LEFT JOIN agents h ON e.assigned_helper = h.id
LEFT JOIN tasks t ON e.task_id = t.id
WHERE e.status != 'resolved';
```

---

## 💬 Communication Patterns

### Pattern 1: Request Help (ติดปัญหา)

```python
# Agent: Dev (Amelia) ติดปัญหา

class AgentCommunication:
    def request_help(
        self, 
        from_agent: str,           # "dev"
        issue: str,                # "Bug: Auth token not refreshing"
        context_task: str,         # "T-20260201-3"
        urgency: str = "high",     # "high"
        suggested_helpers: list = None  # ["architect", "solo-dev"]
    ):
        # 1. บันทึกลง database
        conversation_id = self._create_conversation(
            from_agent=from_agent,
            message_type="help",
            content=issue,
            context_task_id=context_task,
            urgency=urgency
        )
        
        # 2. สร้าง escalation
        escalation_id = self._create_escalation(
            from_agent=from_agent,
            task_id=context_task,
            issue_type="technical",
            description=issue,
            priority=urgency
        )
        
        # 3. หา helper ที่เหมาะสม
        if not suggested_helpers:
            suggested_helpers = self._find_best_helpers(issue_type="technical")
        
        # 4. ส่งข้อความไป helpers
        for helper in suggested_helpers:
            self._send_to_agent(
                to_agent=helper,
                from_agent=from_agent,
                message=f"🆘 Help needed from {from_agent}\n\nIssue: {issue}\nTask: {context_task}\nUrgency: {urgency}",
                conversation_id=conversation_id
            )
        
        # 5. แจ้งเตือน Telegram (สำคัญ!)
        self._notify_telegram(
            f"🆘 {from_agent.upper()} NEEDS HELP\n\n"
            f"Task: {context_task}\n"
            f"Issue: {issue}\n"
            f"Urgency: {urgency}\n"
            f"Notified: {', '.join(suggested_helpers)}"
        )
        
        return escalation_id
```

### Pattern 2: Broadcast Update (แจ้งทีม)

```python
# Agent: Scrum Master (Bob) แจ้งทีม

def broadcast_update(
    self,
    from_agent: str,      # "scrum-master"
    message: str,         # "Sprint planning tomorrow 10:00"
    urgency: str = "normal"
):
    # 1. บันทึกลง database (to_agent = NULL = broadcast)
    conversation_id = self._create_conversation(
        from_agent=from_agent,
        to_agent=None,  # Broadcast
        message_type="update",
        content=message,
        urgency=urgency
    )
    
    # 2. ส่งไปทุก Agent ที่ subscribe
    subscribed_agents = self._get_subscribed_agents("update")
    for agent in subscribed_agents:
        self._send_to_agent(
            to_agent=agent,
            from_agent=from_agent,
            message=f"📢 Broadcast from {from_agent}:\n{message}",
            conversation_id=conversation_id
        )
    
    # 3. แจ้งเตือน Telegram
    self._notify_telegram(
        f"📢 BROADCAST from {from_agent}\n\n{message}"
    )
```

### Pattern 3: Direct Message (คุยกันตัวต่อตัว)

```python
# Agent: Architect (Winston) ตอบกลับ Dev

def send_direct_message(
    self,
    from_agent: str,      # "architect"
    to_agent: str,        # "dev"
    message: str,         # "Check JWT secret in .env"
    reply_to: str = None,  # conversation_id ที่ตอบกลับ
    context_task: str = None
):
    # 1. บันทึกลง database
    conversation_id = self._create_conversation(
        from_agent=from_agent,
        to_agent=to_agent,
        message_type="answer",
        content=message,
        parent_message_id=reply_to,
        context_task_id=context_task
    )
    
    # 2. ส่งไป Agent ปลายทาง
    self._send_to_agent(
        to_agent=to_agent,
        from_agent=from_agent,
        message=f"💬 {from_agent}:\n{message}",
        conversation_id=conversation_id
    )
    
    # 3. แจ้งเตือน Telegram (เพื่อให้ผู้ใช้รับรู้)
    self._notify_telegram(
        f"💬 {from_agent} → {to_agent}\n\n"
        f"Task: {context_task or 'N/A'}\n"
        f"Message: {message}"
    )
    
    # 4. ถ้าเป็นการตอบ help request ให้อัปเดต escalation
    if reply_to:
        self._update_escalation_with_response(reply_to, from_agent, message)
```

---

## 📱 Telegram Notification Format

### 1. Help Request
```
🆘 DEV NEEDS HELP

Task: T-20260201-3
Issue: Bug in auth - token not refreshing
Urgency: HIGH ⏰

Notified: architect, solo-dev

[View Details] [Assign Helper] [Mark Resolved]
```

### 2. Direct Reply
```
💬 ARCHITECT → DEV

Task: T-20260201-3
Re: Bug in auth

Message:
Check JWT secret in .env file. 
Also verify token expiry time.

[View Thread] [Reply] [Mark Resolved]
```

### 3. Broadcast
```
📢 BROADCAST from SCRUM-MASTER

Sprint planning moved to tomorrow 10:00 AM.
Please prepare your updates.

[Acknowledge] [View Calendar]
```

### 4. Escalation Resolved
```
✅ ISSUE RESOLVED

Task: T-20260201-3
Issue: Bug in auth

Solution by: architect
"JWT secret was outdated. Updated and tested."

Time to resolve: 15 minutes

[View Details] [Close Thread]
```

---

## 🔧 Implementation

### File: `~/clawd/memory/team/comm/message_router.py`

```python
#!/usr/bin/env python3
"""
AI Team Message Router
Central hub for agent-to-agent communication
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from team_db import AITeamDB

class MessageRouter:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path(__file__).parent.parent / "messages.db"
        self.init_database()
        self.team_db = AITeamDB()
        
    def init_database(self):
        """Initialize messages database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables (from schema above)
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                from_agent TEXT NOT NULL,
                to_agent TEXT,
                message_type TEXT,
                content TEXT NOT NULL,
                context_task_id TEXT,
                urgency TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'unread',
                parent_message_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                read_at DATETIME,
                FOREIGN KEY (parent_message_id) REFERENCES conversations(id)
            );
            
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_id TEXT NOT NULL,
                conversation_id TEXT,
                channel TEXT DEFAULT 'telegram',
                content TEXT NOT NULL,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                delivered BOOLEAN DEFAULT FALSE,
                read_by_user BOOLEAN DEFAULT FALSE
            );
            
            CREATE TABLE IF NOT EXISTS escalations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                escalation_id TEXT NOT NULL,
                task_id TEXT,
                from_agent TEXT NOT NULL,
                issue_type TEXT,
                description TEXT NOT NULL,
                assigned_helper TEXT,
                status TEXT DEFAULT 'open',
                priority TEXT DEFAULT 'normal',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME,
                resolution_notes TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_conv_from ON conversations(from_agent);
            CREATE INDEX IF NOT EXISTS idx_conv_to ON conversations(to_agent);
            CREATE INDEX IF NOT EXISTS idx_conv_task ON conversations(context_task_id);
            CREATE INDEX IF NOT EXISTS idx_conv_status ON conversations(status);
            CREATE INDEX IF NOT EXISTS idx_esc_status ON escalations(status);
        ''')
        
        conn.commit()
        conn.close()
    
    def request_help(
        self,
        from_agent: str,
        issue: str,
        context_task: str = None,
        urgency: str = "normal",
        suggested_helpers: List[str] = None
    ) -> str:
        """
        Agent requests help from other agents
        Notifies: suggested helpers + Telegram
        """
        escalation_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        conversation_id = f"CONV-{uuid.uuid4().hex[:8].upper()}"
        
        conn = sqlite3.connect(self.db_path)
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
            
            # 4. Send to helpers
            for helper in suggested_helpers:
                self._send_to_agent_session(helper, from_agent, issue, context_task, urgency)
            
            # 5. IMPORTANT: Notify Telegram
            self._notify_telegram(
                f"🆘 {from_agent.upper()} NEEDS HELP\n\n"
                f"Escalation: {escalation_id}\n"
                f"Task: {context_task or 'N/A'}\n"
                f"Issue: {issue}\n"
                f"Urgency: {urgency.upper()}\n"
                f"Notified: {', '.join(suggested_helpers)}"
            )
            
            return escalation_id
            
        finally:
            conn.close()
    
    def reply_to_help(
        self,
        from_agent: str,
        to_agent: str,
        reply_message: str,
        escalation_id: str,
        context_task: str = None
    ) -> bool:
        """
        Agent replies to help request
        Notifies: original requester + Telegram
        """
        conversation_id = f"CONV-{uuid.uuid4().hex[:8].upper()}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
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
            
            # 3. Send to original requester
            self._send_to_agent_session(
                to_agent, 
                from_agent, 
                f"💬 Reply from {from_agent}:\n{reply_message}",
                context_task,
                'normal'
            )
            
            # 4. IMPORTANT: Notify Telegram
            self._notify_telegram(
                f"💬 {from_agent.upper()} → {to_agent.upper()}\n\n"
                f"Escalation: {escalation_id}\n"
                f"Task: {context_task or 'N/A'}\n"
                f"Reply: {reply_message}"
            )
            
            return True
            
        finally:
            conn.close()
    
    def resolve_escalation(
        self,
        escalation_id: str,
        resolution_notes: str,
        resolved_by: str
    ) -> bool:
        """
        Mark escalation as resolved
        Notifies: all involved + Telegram
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get escalation details
            cursor.execute('''
                SELECT from_agent, assigned_helper, task_id, description
                FROM escalations WHERE escalation_id = ?
            ''', (escalation_id,))
            row = cursor.fetchone()
            
            if not row:
                return False
            
            from_agent, helper, task_id, issue = row
            
            # Update escalation
            cursor.execute('''
                UPDATE escalations 
                SET status = 'resolved', 
                    resolved_at = CURRENT_TIMESTAMP,
                    resolution_notes = ?
                WHERE escalation_id = ?
            ''', (resolution_notes, escalation_id))
            
            conn.commit()
            
            # Notify involved agents
            involved = [a for a in [from_agent, helper, resolved_by] if a]
            for agent in set(involved):
                self._send_to_agent_session(
                    agent,
                    'system',
                    f"✅ Issue resolved by {resolved_by}\n\n{resolution_notes}",
                    task_id,
                    'normal'
                )
            
            # IMPORTANT: Notify Telegram
            self._notify_telegram(
                f"✅ ISSUE RESOLVED\n\n"
                f"Escalation: {escalation_id}\n"
                f"Task: {task_id or 'N/A'}\n"
                f"Issue: {issue}\n"
                f"Resolved by: {resolved_by}\n"
                f"Solution: {resolution_notes}"
            )
            
            return True
            
        finally:
            conn.close()
    
    def _find_best_helpers(self, issue: str) -> List[str]:
        """Find best agents to help based on issue type"""
        # Simple keyword matching - can be enhanced with ML
        issue_lower = issue.lower()
        
        if any(k in issue_lower for k in ['database', 'sql', 'schema']):
            return ['architect', 'dev']
        elif any(k in issue_lower for k in ['ui', 'css', 'design', 'layout']):
            return ['ux-designer', 'dev']
        elif any(k in issue_lower for k in ['test', 'bug', 'error', 'fail']):
            return ['qa', 'solo-dev', 'architect']
        elif any(k in issue_lower for k in ['requirement', 'spec', 'feature']):
            return ['pm', 'analyst']
        else:
            return ['architect', 'solo-dev']  # Default
    
    def _send_to_agent_session(self, agent_id: str, from_agent: str, message: str, task_id: str, urgency: str):
        """Send message to agent's session"""
        # This would use sessions_send in real implementation
        # For now, log it
        print(f"[TO {agent_id}] from {from_agent}: {message[:50]}...")
    
    def _notify_telegram(self, message: str):
        """Send notification to Telegram"""
        # In real implementation, use the message tool
        # For now, print to console
        print(f"\n[TELEGRAM NOTIFICATION]\n{message}\n{'='*50}")


# CLI interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['help', 'reply', 'resolve'])
    parser.add_argument('--from', dest='from_agent', required=True)
    parser.add_argument('--to', dest='to_agent')
    parser.add_argument('--message', '-m', required=True)
    parser.add_argument('--task', '-t')
    parser.add_argument('--escalation', '-e')
    parser.add_argument('--urgency', '-u', default='normal')
    
    args = parser.parse_args()
    
    router = MessageRouter()
    
    if args.action == 'help':
        escalation_id = router.request_help(
            from_agent=args.from_agent,
            issue=args.message,
            context_task=args.task,
            urgency=args.urgency
        )
        print(f"Escalation created: {escalation_id}")
        
    elif args.action == 'reply':
        router.reply_to_help(
            from_agent=args.from_agent,
            to_agent=args.to_agent,
            reply_message=args.message,
            escalation_id=args.escalation,
            context_task=args.task
        )
        
    elif args.action == 'resolve':
        router.resolve_escalation(
            escalation_id=args.escalation,
            resolution_notes=args.message,
            resolved_by=args.from_agent
        )
```

---

## 🧪 ทดสอบระบบ

```bash
# 1. Dev ขอความช่วยเหลือ
cd ~/clawd/memory/team
python3 comm/message_router.py help \
  --from dev \
  --message "Bug: Auth token not refreshing after 1 hour" \
  --task T-20260201-3 \
  --urgency high

# Output:
# [TO architect] from dev: Bug: Auth token not refreshing...
# [TO solo-dev] from dev: Bug: Auth token not refreshing...
# [TELEGRAM NOTIFICATION]
# 🆘 DEV NEEDS HELP
# Escalation: ESC-A1B2C3D4
# ...

# 2. Architect ตอบกลับ
python3 comm/message_router.py reply \
  --from architect \
  --to dev \
  --message "Check JWT secret in .env. Also verify expiry time." \
  --escalation ESC-A1B2C3D4 \
  --task T-20260201-3

# 3. Dev แก้ปัญหาเสร็จ ปิด escalation
python3 comm/message_router.py resolve \
  --escalation ESC-A1B2C3D4 \
  --from dev \
  --message "Fixed! JWT secret was outdated. Updated and tested."
```

---

## 📋 สรุป

**การทำงาน:**
1. Agent ติดปัญหา → ใช้ `request_help()`
2. ระบบหา helper ที่เหมาะสม → ส่งข้อความไป
3. **แจ้ง Telegram ทุกครั้ง** (ผู้ใช้รับรู้)
4. Helper ตอบกลับ → ใช้ `reply_to_help()`
5. **แจ้ง Telegram อีกครั้ง**
6. ปัญหาแก้ได้ → ใช้ `resolve_escalation()`
7. **แจ้ง Telegram สรุปผล**

**ข้อดี:**
- ทุกการสื่อสารบันทึกลง database
- ผู้ใช้รับรู้ทุกอย่างผ่าน Telegram
- Agents ช่วยเหลือกันได้
- มีประวัติย้อนหลัง

**ต้องการให้สร้างไฟล์จริงไหมครับ?** 🎯
