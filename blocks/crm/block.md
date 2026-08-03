# crm

> The data foundation of the Command Center: companies, contacts, and projects — each open project
> carrying a **dated next action** so nothing ever falls through. Generalized from a working system,
> rebuilt **local-first on SQLite** so it needs no external account and no secret.

## What it gives you
A single CLI (`crm.py`) every agent and human uses to record who you're talking to, what deals/
projects are open, and what happens next. Its rules are non-negotiable and live in the tool, not in
good intentions: an open project must have a next action + date ("nothing sleeps"), disqualifying a
company needs a reason, and every mutation logs an event (a learning journal you can mine later).

## What it needs
- **Tools / accounts**: Python 3 only. Storage is a local `crm.db` (SQLite). No cloud, no key.
- **Config the agent must fill**: `CRM_DB` (env) or `--db PATH` — where the database lives. Default:
  next to the script.
- **Depends on blocks**: none. The `prospection`, `email-operator`, and `dashboard` blocks read/write
  through it.

## What's in this block
- `code/crm.py` — the CLI: `add-company`, `set-status`, `add-contact`, `project-add`, `project-move`,
  `project-touch`, `note`, `list`, `show`, `relances`, `stats`. Creates its schema on first run.
- `skill/crm.md` — the usage discipline for agents (read before write, nothing sleeps, log interactions).
- `SETUP.md` — install & operate.

## How the agent installs it
Copy `code/crm.py` into `command-center/crm/`, set `CRM_DB` (default is fine), run `python3 crm.py
init` once. Install `skill/crm.md`. See `SETUP.md`.

## v1 scope (honest)
This is the core relationship + pipeline model with the "nothing sleeps" discipline. Prospecting
sequences and follow-up cadences live in the `prospection` block (which extends the same database).
A richer analytics/MRR view can be added later; the event log already captures the history for it.

## Safety
Local file, no external calls, no secrets. Inherits the brain's safety floor for anything an agent
does *with* the data (e.g. emailing a contact is an `email-operator`/finalization concern, not a CRM one).
