# MEMORY.md

## Templates
- Moomsabaii daily finance report template (Telegram-safe ASCII table, English-only, A→Z categories, exclude CashExchange from income): `templates/moomsabaii_daily_finance_report_template.txt`

## Operating modes
- **Party Mode (per obsidian-vault/CLAUDE.md):** when Boat says `Party Mode: <topic>`, spawn 3–5 subagents (roles), run in parallel with deep thinking (prefer `opus`/`sonnet`), then cross-talk + consensus.
- **Parallelization default:** for multi-step/ambiguous tasks, split into parallel subagent workstreams (audit/search/plan vs implementation), then merge and execute.
- **Model fit heuristic:**
  - Codex (this agent): repo edits, scripts, automation, CLI ops.
  - Claude: long-form writing/SOPs, structure of notes.
  - Gemini: fast exploration/alternatives, broad summaries.
