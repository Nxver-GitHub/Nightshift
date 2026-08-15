# runtime — the loop leaves the laptop (US-1.4)

The base kit's runtime is `start-taskrunner.sh`: `caffeinate` + a PID lock — a laptop script. A
company that stops when a lid closes is a demo, not a company. This block moves the whole spine —
taskrunner tick, approver tick, sale recorder, dashboard — into a **Superserve persistent
Firecracker microVM**, where `pause()` checkpoints full VM state (memory, processes, filesystem)
and `resume()` restores it exactly. Kill the laptop; the company keeps running.

Two deliberate design points, because this is a judged repo:

1. **The VM never holds a real credential.** Keys are bound through Superserve *Secrets*: the
   sandbox env carries a stand-in proxy token, and the real value is attached only at egress to
   the provider. Even a fully compromised company VM cannot leak its own Pioneer or Stripe key.
2. **Control plane is stdlib-only.** `runtime.py` speaks Superserve's published REST API
   (openapi.yaml, fetched 2026-08-15) through `urllib` — the same zero-pip idiom as `pay.py`.
   One `_request` per plane, so the test suite runs offline by replacing two symbols.

## Credentials this block DECLARES (names only — values never live in this repo)

| Name | Where the value lives | Used for |
|---|---|---|
| `SUPERSERVE_API_KEY` | operator's env (`ss_live_…`) | control plane: create/pause/resume/kill |
| `pioneer-key` *(Superserve secret name)* | Superserve console → Secrets | bound to `ANTHROPIC_API_KEY`; Claude Code calls Pioneer's compatible endpoint |
| `stripe-key` *(Superserve secret name)* | Superserve console → Secrets | bound to `STRIPE_API_KEY` in the VM |

The per-sandbox `access_token` (data plane) is stored in a git-ignored, `0600` state file next to
`runtime.py` — it is a credential and is treated like one.

## Files

- `code/runtime.py` — CLI: `deploy | status | url | exec | pull | pause | resume | kill`
- `code/supervisor.sh` — runs INSIDE the VM: ticks the approver + taskrunner, keeps the dashboard up
- `code/tick-taskrunner.sh` — one headless taskrunner pass (mirrors `run-approver.sh`'s proven
  flags-in-prompt + scoped-permissions pattern)
- `SETUP.md` — runbook, written for a stranger
- `tests/test_runtime.py` — offline, transport-mocked

## Demo-day fallback (per the release plan risk table)

If provisioning fails by 11:30, run `start-taskrunner.sh` + cron'd `run-approver.sh` on the
laptop and say so on stage. `runtime.py deploy` is additive — nothing in the laptop path is
modified, so the fallback is "don't run one command", not a rollback.
