# Changelog — Nightshift

Append-only. Newest entries on top. Date format `YYYY-MM-DD`.

## 2026-08-03 — connectors guidance (agnostic, Composio recommended)
- Added `blocks/connectors.md`: what actually needs a connector (only email-operator, prospection's
  send step, and content-agents — everything else is local), and the recommendation. Kit stays
  connector-agnostic; **Composio** is the recommended default (handles OAuth, most apps, least wiring),
  with native MCP / CLI as equally valid alternatives.
- Pointed to it from `blocks/README.md`, `email-operator` (block.md + SETUP), and `prospection` SETUP.
- No secret ever in git — credentials live in the connector's own store.

## 2026-08-03 — three more blocks: goals, health, sessions
- `goals` — `goal.py`/`goals.json` + the goal-agent role: carries one background objective (calibrate
  → measurable plan → create dated tasks for the taskrunner → wake on cadence to measure/adjust), with
  the autonomy contract and two escalation levels. Tested. Added `--goal` to the taskrunner's
  `add_task.py` so goal-owned tasks link back.
- `health` — `healthcheck.py` (constate the Command Center; unknown-not-red discipline; always exit 0;
  files a taskrunner ticket on red) + `health-log.py` (tests/improvements/incidents journal). Tested.
- `sessions` — `session-cycle.py` (count runs per persistent agent, reset cleanly so the launcher
  relaunches fresh) + `list-sessions.py` (find a project's attributed Claude Code session). Tested.
- All generalized, config-driven, no secrets. Catalog: 10/10 built.

## 2026-08-03 — the other six blocks (all built)
- `crm` — local-first SQLite CRM (`crm.py`): companies/contacts/projects/interactions/events, with
  the embedded rules (nothing sleeps → open project needs a dated next action; disqualify needs a
  reason; every mutation logs an event). Tested.
- `prospection` — `prospection.py`: 3–4 step email sequences on the same DB, with a hard validation
  gate (nothing sendable until the owner approves) + the outbound role skill. Tested.
- `email-operator` — role skill (connector-agnostic) + `state.py` (already-handled tracker) +
  `run-operator.sh`. Triages the inbox, drafts, delegates multi-step to the taskrunner, never sends. Tested.
- `content-agents` — per-network content role skill (never publishes; owner posts, returns the URL) +
  `content.py` pipeline (idea→draft→ready→posted + stats). Tested.
- `dashboard` — minimal read-only local view (`server.py` stdlib HTTP + self-contained `index.html`)
  over tasks.json + crm.db + the brain. No build step. Tested (API + page serve).
- `scheduled-tasks` — `run-scheduled.sh` (review-mode headless pass of any skill) + cron/launchd/systemd
  templates. The periodic complement to the taskrunner's persistent loop.
- All generalized, config-driven, no secrets; full leak audit across `blocks/` = 0 matches. Catalog: all built.

## 2026-08-03 — taskrunner runtime + operate runbook
- Added the "trigger" layer so the block runs like the source system: `code/start-taskrunner.sh`
  (persistent `claude --remote-control … "/loop /taskrunner"` session + auto-relaunch + `.taskrunner.on`
  on/off flag + PID anti-double-instance lock + macOS `caffeinate` keep-awake, no-op elsewhere) and
  `code/stop-taskrunner.sh`.
- Added `SETUP.md` — the install & operate runbook for the founder's Claude Code: place code, install
  the skill into `~/.claude/skills/taskrunner/SKILL.md`, configure via env (no secrets), start, verify,
  operate, plus the `--permission-mode auto` + finalization-gate safety rationale and platform notes.
- Config-driven: `TASKRUNNER_DIR/SESSION/MODEL/SKILL`. Launcher tested (syntax, anti-double-instance
  guard, clean stop); the live `claude` invocation isn't runnable in CI but its surrounding logic is.

## 2026-08-03 — first block: taskrunner
- Built `blocks/taskrunner/` — the first real block, generalized from a working system.
- `code/`: `add_task.py`, `update_task.py`, `list_tasks.py`, seed `tasks.json`. Atomic, lock-based,
  concurrency-safe writes; visible plan (steps); owner question + finalization gate for irreversible
  gestures; due-date reschedule counter. Config-driven: `TASKRUNNER_OWNER`, `TASKRUNNER_TASKS`/`--tasks`.
- `skill/taskrunner.md`: the role — tick loop, claim-before-work, "the runner judges completion",
  reversible/irreversible boundary, close-and-update-the-brain.
- No secrets, no hardcoded paths, "the owner" replaces any specific person. Smoke-tested end to end
  (add → claim → steps → finalize → guards → board); all three scripts compile.
- Catalog updated: `taskrunner` = built.

## 2026-08-03 — blocks layer (framework)
- Introduced the second layer: `blocks/` — a catalog of generalized, config-driven capabilities the
  founder's agent consolidates into their own private Command Center.
- Added `blocks/README.md` (the catalog + consolidation flow), `blocks/_TEMPLATE/block.md` (block
  anatomy), and the `/sunday-assemble` command.
- Documented two layers (brain, then blocks) in `README.md`; added Step 8 (assemble) to `START-HERE.md`.
- Candidate blocks to generalize from the source system (all `planned`): dashboard, taskrunner, email-operator,
  crm, prospection, content-agents, scheduled-tasks. Each ships generalized — no secrets, no hardcoded
  wiring. Repo is private.

## 2026-08-03 — v0 scaffold
- Created the kit skeleton: installer director (`CLAUDE.md`), `/sunday` command, `README.md`,
  `START-HERE.md` runbook.
- Wrote `kit/ontology.md` (the Company Brain rules, generalized and stripped of any real data).
- Added `kit/templates/` (routing hub, brain entry point, per-entity template, people/positioning/tools notes).
- Wrote the founding interview protocol `kit/interview/company.md` (create-a-company mode).
  `kit/interview/personal.md` is a stub — personal mode comes later.
- Added a fictional worked example under `examples/acme-brain/` to show a finished brain.
- Public repo in English; first end-to-end mode = company creation.
