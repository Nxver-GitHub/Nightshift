# health

> Self-monitoring so failures don't stay silent. One check that CONSTATES the Command Center's state
> (kanban valid, no stale claims, CRM reachable) and — when a signal goes red — files a taskrunner
> task, turning a silent failure into a ticket the system picks up on its own. Plus a journal of what
> you changed between measurements. Generalized from a working system.

## What it gives you
- `healthcheck.py` — a read-or-act check that returns a JSON verdict and, on a red signal, optionally
  creates a high-priority taskrunner task. Its governing rule: **every signal may be false without
  crying** (unknown when a source is unreadable, never red by default; an exemptions file; always
  exits 0 so a scheduler never loops on the checker's own status).
- `health-log.py` — a dated journal of tests, improvements, and incidents, so a drop in health can be
  traced to the change that caused it.

## What it needs
- **Tools / accounts**: Python 3. Reads the taskrunner's `tasks.json` and the crm's `crm.db` if their
  env vars are set; each check degrades to `unknown` when its source is missing.
- **Config the agent must fill**: `TASKRUNNER_TASKS`, `CRM_DB`, `HEALTH_ADD_TASK` (path to the
  taskrunner's add_task.py, to enable task creation on red), and `healthcheck.json` (exemptions).
- **Depends on blocks**: none hard. Most useful with `taskrunner` (to file tickets) and `crm`.

## What's in this block
- `code/healthcheck.py` + `code/healthcheck.json` — the check + exemptions.
- `code/health-log.py` — the tests/improvements/incidents journal (JSONL, append-only, locked).
- `SETUP.md` — install & schedule.

## How the agent installs it
Copy `code/` into `command-center/health/`; point the env vars at the other blocks; run it by hand,
then schedule it with the `scheduled-tasks` block (e.g. every 30 min). See `SETUP.md`.

## v1 scope (honest)
Ships three generic checks (kanban validity, stale claims, CRM reachability). It's designed to grow:
add checks for whatever you run (a scheduled job's freshness, a service's reachability) following the
same "unknown-not-red, always exit 0" discipline.

## Safety
Read-only except creating a taskrunner task on a red signal (behind `HEALTH_ADD_TASK`). It fixes
nothing on its own — a red becomes a ticket, and the taskrunner (with its finalization gate) handles it.
