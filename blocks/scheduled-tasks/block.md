# scheduled-tasks

> Run any skill on a schedule — the periodic complement to the taskrunner's always-on `/loop`
> session. One generic runner plus cron / launchd / systemd templates. Review-mode first: the agent
> prepares, a human approves anything irreversible, and it's promoted to fuller autonomy only once proven.

## What it gives you
A single wrapper (`run-scheduled.sh <skill>`) that runs one headless Claude Code pass of a skill and
logs it, plus ready-to-edit scheduler templates for macOS (launchd), Linux (systemd), and cron. Use
it to fire the `email-operator` every 30 min, send the `prospection` batch once a day, run a health
check nightly — anything you'd rather trigger on a clock than keep looping.

## What it needs
- **Tools / accounts**: Claude Code (headless `claude -p`), a bash shell, and the OS scheduler (cron/
  launchd/systemd). The machine must be awake for a run to fire.
- **Config the agent must fill**: `SCHED_MODEL` (default `claude-opus-5`), absolute paths in whichever
  template you use.
- **Depends on blocks**: none directly — it triggers *other* blocks' skills (`email-operator`,
  `prospection`, …).

## What's in this block
- `code/run-scheduled.sh` — the generic runner (one review-mode pass of a named skill, with logging).
- `code/templates/cron.txt` — crontab lines (macOS/Linux).
- `code/templates/launchd.plist` — macOS LaunchAgent (StartInterval).
- `code/templates/systemd.service` + `systemd.timer` — Linux user timer.
- `SETUP.md` — install per OS.

## Persistent loop vs periodic — when to use which
- **Persistent `/loop`** (the taskrunner's launcher): reactive, chains work, stays live. Best for the
  taskrunner itself.
- **Periodic (this block)**: simpler, no always-on session, latency up to the interval. Best for
  inbox triage, daily batches, health checks.

## Safety
Every scheduled run is **review-mode**: the wrapper's prompt tells the agent to prepare everything
reversible and stop before anything irreversible until a human confirms. Promote a job to fuller
autonomy only after it's proven itself. This is the brain's safety floor, on a timer.
