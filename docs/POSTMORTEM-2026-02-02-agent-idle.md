# Post-Mortem: Agent Idle Issue

## Date: 2026-02-02

## Problem
- มี Tasks 11 งานใน queue (TODO) แต่ไม่มี Agent คนไหนทำงาน
- ทุก Agent อยู่สถานะ IDLE
- ไม่มี Active Sessions

## Root Causes

### 1. Missing Task Spawn Trigger ❌
```
What happened:
  CREATE task → ADD to database → STOP
  
What should happen:
  CREATE task → ADD to database → SPAWN agent → START work
```

**Problem:** ระบบสร้าง task ใน database แต่ไม่มีการ spawn agent session จริง

### 2. No Auto-Assignment Logic ❌
- Tasks ถูกสร้างด้วย `assignee_id` แต่ไม่มีการเริ่มงานอัตโนมัติ
- ต้องมี trigger ที่ spawn agent เมื่อ task ถูกสร้าง/มอบหมาย

### 3. No Active Monitoring ❌
- ไม่มีระบบตรวจสอบว่า agent กำลังทำงานอยู่จริง
- Heartbeat ไม่ถูก update

## Solution Implemented

### Immediate Fix
1. Spawn 3 agents สำหรับงาน Critical/High:
   - Story 5: Line OA (Dev)
   - Kanban Dashboard (UX)
   - Duration Tracking (Architect)

2. Update database status → in_progress

### Long-term Prevention

#### Workflow Update Required
```
NEW RULE: Every task creation MUST trigger agent spawn

ON task_create:
  1. Insert to database
  2. IF assignee_id IS NOT NULL:
       - SPAWN agent immediately
       - UPDATE agent.status = 'active'
       - UPDATE task.status = 'in_progress'
  3. NOTIFY user (Telegram)

ON task_complete:
  1. Auto-check for next available task
  2. IF available AND agent capacity not full:
       - Auto-assign next task
       - SPAWN agent for next task
```

#### Add Task Queue Monitor
- Cron job every 15 min: Check for TODO tasks with assignee but no active session
- Auto-spawn if agent idle

#### Add Escalation
- ถ้างาน TODO > 30 min ไม่มีคนทำ → แจ้ง Telegram → Auto-assign Solo Dev

## Prevention Checklist

- [ ] อัพเดต workflow: Task creation → Auto-spawn
- [ ] เพิ่ม Task Queue Monitor (cron)
- [ ] เพิ่ม Escalation rule: TODO > 30 min → Auto-assign
- [ ] เพิ่ม Heartbeat check: Agent idle > 1h → Alert

## Action Items

1. Update AI-TEAM-SYSTEM.md with new workflow rules
2. Create task_spawn_helper.sh สำหรับ auto-spawn
3. Add cron job: task-queue-monitor (every 15 min)
