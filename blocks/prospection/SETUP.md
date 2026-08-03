# Prospection — install & operate

> For the founder's Claude Code agent. Requires the `crm` block (same database).

## Install
1. Install the `crm` block first. Note its `CRM_DB` path.
2. Copy `code/prospection.py` into `command-center/prospection/`.
3. Point it at the **same** database: `export CRM_DB=/path/to/crm.db` (the crm block's DB).
4. Install the skill: `mkdir -p ~/.claude/skills/prospection && cp blocks/prospection/skill/prospection.md ~/.claude/skills/prospection/SKILL.md`,
   and set `$PROS` (prospection.py) and `$CRM` (crm.py) inside it.

## Operate
- One session per prospecting push, or a daily task on the `taskrunner`: run the loop in `skill/prospection.md`.
- Daily send: `python3 prospection.py due-today` → send each approved step via your email path →
  `mark-sent`. **Only approved steps ever appear here** — the owner approves with
  `python3 prospection.py approve --sequence <id>`.
- A reply: `python3 prospection.py reply-received --contact <id>`, then log it in the CRM.

## Build your script library
The block ships mechanics, not copy. Keep your best-performing email sequences as notes in the brain
(e.g. `<company>/notes/prospection-scripts.md`) and reuse them. Tune from replies; the CRM's event
log is your evidence.

## Safety
Sending is gated: nothing leaves without `approve`. Keep bulk sending and any committing message
behind the owner's explicit yes (brain safety floor).
