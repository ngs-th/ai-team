# Files vs SQLite: การเปรียบเทียบสำหรับ AI Team

**Date:** 2026-02-01  
**Context:** เลือกระบบจัดเก็บข้อมูล Task & Progress สำหรับ AI Team

---

## 📊 ตารางเปรียบเทียบ

| หัวข้อ | Files (MD/JSON) | SQLite | ข้อสังเกต |
|--------|----------------|--------|-----------|
| **อ่านง่าย** | ⭐⭐⭐⭐⭐ | ⭐⭐ | Files อ่านได้ทันที |
| **เขียนง่าย** | ⭐⭐⭐⭐ | ⭐⭐⭐ | Files append ง่าย |
| **Query ข้อมูล** | ⭐⭐ | ⭐⭐⭐⭐⭐ | SQL ง่ายกว่า parse JSON |
| **Concurrent Access** | ⭐⭐ | ⭐⭐⭐⭐ | SQLite รองรับหลาย reader |
| **Data Integrity** | ⭐⭐ | ⭐⭐⭐⭐⭐ | SQLite มี ACID |
| **Version Control** | ⭐⭐⭐⭐⭐ | ⭐⭐ | Git diff ไฟล์ง่ายกว่า |
| **Backup/Restore** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ทั้งคู่ทำได้ |
| **Scaling** | ⭐⭐ | ⭐⭐⭐⭐ | SQLite รับข้อมูลมากกว่า |
| **Setup Complexity** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Files ไม่ต้อง setup |
| **Tool Ecosystem** | ⭐⭐⭐ | ⭐⭐⭐⭐ | SQLite มี tool มาก |

---

## ✅ ข้อดีของแต่ละแบบ

### Files (Markdown + JSON)

```
Pros:
✅ Human-readable - เปิดอ่านได้ทันที
✅ Git-friendly - diff ง่าย, track changes
✅ Zero setup - ไม่ต้องติดตั้งอะไร
✅ Flexible schema - แก้โครงสร้างได้ตลอด
✅ Portable - ย้ายไม่อยู่ที่ไหนก็ได้

Cons:
❌ Query ยาก - ต้อง parse JSON เอง
❌ No ACID - กลัวข้อมูลเสียตอน concurrent write
❌ No relationships - เชื่อมโยงข้อมูลยาก
❌ Locking issues - หลาย Agent อ่าน/เขียนพร้อมกันอาจมีปัญหา
```

### SQLite

```
Pros:
✅ ACID compliant - ข้อมูลไม่เสียแน่นอน
✅ SQL queries - ดึงข้อมูลซับซ้อนได้
✅ Concurrent reads - หลาย Agent อ่านพร้อมกันได้
✅ Relationships - FOREIGN KEY, JOIN ได้
✅ Performance - เร็วกับข้อมูลมากๆ
✅ Atomic writes - อัปเดตหลายตารางพร้อมกันได้

Cons:
❌ Binary file - Git diff ยาก
❌ Setup required - ต้องสร้าง schema
❌ Not human-readable - ต้องใช้ tool อ่าน
❌ Write locking - เขียนพร้อมกันอาจติด lock
```

---

## 🎯 แนะนำสำหรับ AI Team

### Option A: Hybrid (แนะนำ) ⭐

```
📁 Files (Markdown) - สำหรับคนอ่าน
   ├── TASK-BOARD.md        # Kanban แบบมองเห็นได้
   ├── PROJECT-STATUS.md    # Dashboard สรุป
   └── DAILY-REPORTS/       # รายงานประจำวัน

🗄️ SQLite - สำหรับ Machine
   ├── tasks table          # ข้อมูล tasks ทั้งหมด
   ├── agents table         # สถานะ agents
   ├── projects table       # ข้อมูลโปรเจค
   └── history table        # Log การเปลี่ยนแปลง

🔄 Sync: SQLite → Markdown (auto generate)
```

**ข้อดี:**
- คนอ่านได้จาก Markdown
- Agent อ่าน/เขียน SQLite เร็ว
- มี ACID guarantees
- Query ข้อมูลง่าย

---

### Option B: Files Only (เริ่มต้น)

```
📁 ~/clawd/memory/team/
   ├── active-tasks.json    # Tasks ปัจจุบัน
   ├── agent-status.json    # สถานะ agents
   ├── PROJECT-STATUS.md    # Dashboard
   └── TASK-BOARD.md        # Kanban board
```

**เหมาะเมื่อ:**
- ทีมเล็ก (< 5 agents active)
- Tasks ไม่เยอะ (< 100)
- ไม่ต้องการ query ซับซ้อน
- ต้องการ Git history ชัดเจน

---

### Option C: SQLite Only (Production)

```
🗄️ ~/clawd/memory/team.db
   ├── tasks
   ├── agents  
   ├── projects
   ├── sprints
   └── history

📄 Export to Markdown (อ่าน-only)
   ├── TASK-BOARD.md (auto-generated)
   └── PROJECT-STATUS.md (auto-generated)
```

**เหมาะเมื่อ:**
- ทีมใหญ่ (> 5 agents)
- Tasks เยอะ (> 100)
- ต้องการ analytics
- ต้องการ query ซับซ้อน

---

## 🏗️ โครงสร้าง SQLite (ถ้าเลือก)

```sql
-- tasks table
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    assignee TEXT,           -- agent id: pm, dev, qa, etc.
    status TEXT,             -- todo, in_progress, done, blocked
    priority TEXT,           -- critical, high, normal, low
    progress INTEGER,        -- 0-100
    project_id TEXT,
    created_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    eta DATETIME,
    blocked_by TEXT,         -- task id ที่ติด
    notes TEXT
);

-- agents table
CREATE TABLE agents (
    id TEXT PRIMARY KEY,     -- pm, dev, qa, etc.
    name TEXT,
    status TEXT,             -- idle, active, blocked
    current_task_id TEXT,
    last_heartbeat DATETIME,
    total_tasks_completed INTEGER,
    FOREIGN KEY (current_task_id) REFERENCES tasks(id)
);

-- projects table
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT,
    status TEXT,             -- planning, active, completed
    start_date DATE,
    end_date DATE,
    progress INTEGER         -- calculated from tasks
);

-- history/log table
CREATE TABLE task_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    agent_id TEXT,
    action TEXT,             -- created, started, updated, completed
    old_status TEXT,
    new_status TEXT,
    old_progress INTEGER,
    new_progress INTEGER,
    timestamp DATETIME,
    notes TEXT
);

-- views สำหรับ dashboard
CREATE VIEW v_agent_workload AS
SELECT 
    a.id as agent_id,
    a.name,
    COUNT(t.id) as active_tasks,
    AVG(t.progress) as avg_progress
FROM agents a
LEFT JOIN tasks t ON a.id = t.assignee AND t.status = 'in_progress'
GROUP BY a.id;

CREATE VIEW v_project_status AS
SELECT 
    p.id,
    p.name,
    COUNT(t.id) as total_tasks,
    SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) as done_tasks,
    ROUND(100.0 * SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) / COUNT(t.id), 2) as progress_pct
FROM projects p
LEFT JOIN tasks t ON p.id = t.project_id
GROUP BY p.id;
```

---

## 💡 คำแนะนำ

### สำหรับเริ่มต้น (แนะนำ): **Hybrid**

```python
# โครงสร้างที่แนะนำ
~/clawd/memory/
├── team/
│   ├── team.db              # SQLite - ข้อมูลหลัก
│   ├── TASK-BOARD.md        # Auto-generated from SQLite
│   └── PROJECT-STATUS.md    # Auto-generated from SQLite
│
└── agents/
    └── ...

# วิธีทำงาน:
1. Agents อ่าน/เขียน SQLite โดยตรง
2. Orchestrator สร้าง Markdown reports จาก SQLite
3. User อ่าน Markdown ผ่าน Telegram หรือ cat
```

**เหตุผล:**
- ✅ ได้ ACID จาก SQLite
- ✅ Query ข้อมูลง่าย
- ✅ คนอ่านได้จาก Markdown
- ✅ Git track ได้ (Markdown เปลี่ยนตาม SQLite)
- ✅ Scale ได้เมื่อทีมโต

---

## 🚀 การตัดสินใจ

| ถ้า... | เลือก... |
|--------|---------|
| อยากเริ่มเร็ว ไม่ยุ่งยาก | **Files Only** |
| ต้องการความน่าเชื่อถือ อนาคต scale | **Hybrid** ⭐ |
| ทีมใหญ่ ข้อมูลเยอะ | **SQLite Only** |
| ต้องการ Git diff ชัดเจนที่สุด | **Files Only** |

---

**แนะนำของผม:** เริ่มด้วย **Hybrid** ตั้งแต่วันแรก
- SQLite เก็บข้อมูลจริง
- Markdown สร้าง auto จาก SQLite
- ได้ความสามารถทั้งสองแบบ

**ต้องการให้สร้างแบบไหนครับ?** 🎯
