# CRM — install & operate

> For the founder's Claude Code agent. Local-first; no account, no secret.

## Install
1. Copy `code/crm.py` into `command-center/crm/`.
2. Choose where the database lives: default `crm.db` next to the script, or set `CRM_DB=/path/crm.db`.
   Keep the DB **out of any public repo** — it holds real customer data. (The kit's `.gitignore`
   already blocks generated brains; make sure the command-center lives in the private brain, not here.)
3. Initialize: `python3 command-center/crm/crm.py init`.
4. Install the skill: `mkdir -p ~/.claude/skills/crm && cp blocks/crm/skill/crm.md ~/.claude/skills/crm/SKILL.md`,
   and set `$CRM` in it to the crm.py path.

## Operate
- Add and advance work with the commands in `skill/crm.md`.
- On every review, run `python3 crm.py relances` — it surfaces open projects that are due, overdue,
  or (a bug) missing a next action. Fix each: `project-touch` or `project-move`.
- Back the DB up like any file (it's plain SQLite): copy `crm.db`, or keep the private brain in git.

## Notes
- No network, no key — everything is in the local SQLite file.
- Statuses/stages are generic; adapt the lists at the top of `crm.py` to your business if needed
  (keep the "nothing sleeps" rule intact — it's the point).
