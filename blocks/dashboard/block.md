# dashboard

> The visible spine of the Command Center: one local page showing the taskrunner kanban, the CRM
> pipeline (and what's due), and the brain's state. Python stdlib only — no build step, no
> dependencies, no external calls. A minimal, honest starting point you can grow.

## What it gives you
A read-only web view at `http://localhost:8787` that reads three things and renders them: the
taskrunner's `tasks.json` (as a kanban), the crm block's `crm.db` (companies, pipeline, due/overdue
next actions), and the brain's `main_brain.md`. It plugs the other blocks together into one screen.

## What it needs
- **Tools / accounts**: Python 3 only (stdlib `http.server`). No framework, no npm.
- **Config the agent must fill**: `DASH_PORT` (8787), `TASKRUNNER_TASKS`, `CRM_DB`, `BRAIN_DIR` —
  point them at the other blocks' files. Each panel degrades gracefully if its source is unset.
- **Depends on blocks**: none hard, but it's most useful with `taskrunner` and `crm` installed.

## What's in this block
- `code/server.py` — a stdlib HTTP server serving the page + a tiny read-only JSON API
  (`/api/tasks`, `/api/crm`, `/api/brain`).
- `code/index.html` — a self-contained, theme-aware page (vanilla HTML/JS/CSS) that renders the board,
  the CRM summary, and the brain snapshot.
- `SETUP.md` — install & run.

## v1 scope (honest)
This is a **minimal, read-only spine**, not a full app. It shows state; it doesn't yet let you add
tasks or a chat from the page (use the CLIs / a Claude Code session for that). It's deliberately
dependency-free so anyone can run it instantly — a richer dashboard can replace it later without
changing the other blocks (they expose files, not APIs).

## Safety
Binds to `127.0.0.1` (localhost only) and is **read-only** — it never mutates the kanban, CRM, or
brain. No external calls, no secrets. Don't expose the port publicly; it shows real business data.
