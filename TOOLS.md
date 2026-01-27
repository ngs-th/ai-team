# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

## ⚠️ Formatting Rules

### Tables = ENGLISH ONLY
- ภาษาไทยมีสระและวรรณยุกต์ทำให้ column spacing เพี้ยน
- ใช้ภาษาอังกฤษในตารางเสมอ ถึงจะคุยเป็นภาษาไทย
- ถ้าต้องแสดงข้อมูลไทย → ใช้ bullet list แทน

## 🔧 OneDrive Lock Fix

When files in OneDrive show "Resource deadlock avoided":

```bash
# Open the parent folder in Finder to trigger sync
open "/Users/ngs/Library/CloudStorage/OneDrive-Personal/obsidian-vault/2-Areas/"

# Wait 3-5 seconds, then retry reading the file
sleep 5 && cat <file_path>
```

If still locked:
```bash
# Restart OneDrive
killall OneDrive
sleep 2
open -a OneDrive
sleep 10
# Then open folder in Finder again
```

**Auto-fix:** When encountering "Resource deadlock avoided" on any OneDrive file, immediately run:
```bash
open "$(dirname '<locked_file_path>')"
```
Then wait 5 seconds and retry.

## What Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases  
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras
- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH
- home-server → 192.168.1.100, user: admin

### TTS
- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## 📄 NGS Document System

เมื่อทำงานเกี่ยวกับเอกสาร NGS (ใบเสนอราคา/ใบแจ้งหนี้/ใบเสร็จ) **ต้องอ่าน SOP ก่อนเสมอ**

**SOP Index:** `/Users/ngs/Library/CloudStorage/OneDrive-Personal/obsidian-vault/Scripts/ngs-doc-export/SOP-INDEX.md`

| งาน | SOP |
|-----|-----|
| สร้าง QT/IV/RC | SOP-Create-Documents.md |
| สรุปค้างจ่าย | SOP-Outstanding-Invoices.md |
| บิล CSTP Email | SOP-CSTP-Billing.md |
| ใบสำคัญจ่าย | SOP-Payment-Voucher.md |

**Database:** `Scripts/ngs-doc-export/ngs_finance.db`

---

## 🛋️ Moomsabaii (มุมสบาย)

เมื่อทำงานเกี่ยวกับมุมสบาย **ต้องอ่าน SOP ก่อน**

**SOP Location:** `/Users/ngs/Library/CloudStorage/OneDrive-Personal/obsidian-vault/Scripts/moomsabaii/`

| งาน | SOP |
|-----|-----|
| Sync ข้อมูลจาก Google Sheet | SOP-GSheet-to-SQLite.md |

**Database:** `Scripts/moomsabaii/moomsabaii.db`

---

## 📋 Kanban Boards

| Board | Location | ใช้สำหรับ |
|-------|----------|----------|
| NGS | `2-Areas/NGS/ngs_kanban.md` | งาน NGS, การเงิน, ลูกค้า |
| Moomsabaii | `2-Areas/Moomsabaii/moomsabaii_kanban.md` | งานมุมสบาย |
| System Ops | `2-Areas/system_ops_kanban.md` | งาน Clawdbot, Infrastructure |

**Base Path:** `/Users/ngs/Library/CloudStorage/OneDrive-Personal/obsidian-vault/`

---

Add whatever helps you do your job. This is your cheat sheet.
