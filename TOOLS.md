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

Add whatever helps you do your job. This is your cheat sheet.
