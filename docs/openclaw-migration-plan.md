# OpenClaw Migration Plan

## Phase 1: Pre-Migration (Backup)

### 1.1 Backup Current Config
```bash
# Backup Moltbot config
cp -r ~/.clawdbot ~/.clawdbot-backup-$(date +%Y%m%d)

# Backup wrapper scripts
cp ~/bin/openclaw-* ~/bin/openclaw-*-backup 2>/dev/null || true

# List current config
echo "=== Current Config ==="
ls -la ~/.clawdbot/
cat ~/.clawdbot/moltbot.json | grep -E "(version|gateway)" | head -5
```

### 1.2 Check Current State
- [ ] Cron jobs ที่ใช้ Moltbot
- [ ] Database locations
- [ ] Custom skills/scripts
- [ ] Telegram bot tokens

---

## Phase 2: Installation

### 2.1 Install OpenClaw
```bash
# Option A: via npm (แนะนำ)
npm install -g openclaw

# Option B: via git
# git clone https://github.com/openclaw/openclaw.git
# cd openclaw && npm install && npm run build
```

### 2.2 Verify Installation
```bash
openclaw --version
openclaw doctor
```

---

## Phase 3: Migration

### 3.1 Auto-Migration (OpenClaw จัดการให้)
```bash
# Run doctor เพื่อ migrate config อัตโนมัติ
openclaw doctor
```

### 3.2 Manual Migration Check
ตรวจสอบว่าไฟล์ถูก migrate ถูกต้อง:
- [ ] `~/.clawdbot/` → ยังคงใช้ได้ (OpenClaw อ่านที่เดิม)
- [ ] Config paths ต่างๆ
- [ ] Database files

### 3.3 Update Cron Jobs (ถ้าจำเป็น)
ถ้ามีการเปลี่ยน path จาก `moltbot` → `openclaw`:
```bash
# Check current cron using moltbot
crontab -l | grep moltbot

# Update ถ้าจำเป็น
# (OpenClaw มี backward compatibility shim อยู่)
```

---

## Phase 4: Multi-Profile Setup

### 4.1 Create Profiles
```bash
# Profile: Work (NGS)
export CLAWDBOT_CONFIG_DIR="$HOME/.clawdbot-work"
export CLAWDBOT_GATEWAY_PORT="18790"
mkdir -p "$CLAWDBOT_CONFIG_DIR"
openclaw doctor

# Profile: Personal
export CLAWDBOT_CONFIG_DIR="$HOME/.clawdbot-personal"
export CLAWDBOT_GATEWAY_PORT="18791"
mkdir -p "$CLAWDBOT_CONFIG_DIR"
openclaw doctor
```

### 4.2 Update Wrapper Scripts
แก้ไข `~/bin/openclaw-work` และ `~/bin/openclaw-personal`:
```bash
#!/bin/bash
export CLAWDBOT_CONFIG_DIR="$HOME/.clawdbot-work"
export CLAWDBOT_GATEWAY_PORT="18790"
exec openclaw "$@"
```

---

## Phase 5: Testing

### 5.1 Test Default Profile
```bash
openclaw status
```

### 5.2 Test Work Profile
```bash
openclaw-work status
```

### 5.3 Test Personal Profile
```bash
openclaw-personal status
```

### 5.4 Verify Telegram Integration
- [ ] ส่งข้อความทดสอบผ่านแต่ละ profile
- [ ] ตรวจสอบว่าไม่ชนกัน

---

## Phase 6: Cleanup

### 6.1 Remove Old Config (หลังจากใช้งานปกติ 1 สัปดาห์)
```bash
# ลบ backup ถ้าทุกอย่างทำงานปกติ
rm -rf ~/.clawdbot-backup-YYYYMMDD
```

### 6.2 Update Documentation
- [ ] อัพเดท TOOLS.md
- [ ] อัพเดท Memory

---

## Rollback Plan (ถ้าผิดพลาด)

```bash
# ย้อนกลับไปใช้ Moltbot
cp -r ~/.clawdbot-backup-YYYYMMDD ~/.clawdbot
npm uninstall -g openclaw
npm install -g moltbot  # ถ้าต้องการ
```

---

## Timeline แนะนำ

| วันที่ | งาน |
|--------|-----|
| Day 1 | Phase 1-2: Backup + Install |
| Day 2 | Phase 3-4: Migration + Multi-profile |
| Day 3 | Phase 5: Testing |
| Day 7+ | Phase 6: Cleanup (ถ้าปกติ) |

---

## Checklist ก่อนเริ่ม

- [ ] ปิด Moltbot gateway ก่อน (`moltbot gateway stop`)
- [ ] Backup ข้อมูลสำคัญ
- [ ] มีเวลาว่าง 2-3 ชั่วโมง
- [ ] Internet connection ปกติ

---

**Status:** ⏳ Waiting to start
**Created:** 2026-01-31
