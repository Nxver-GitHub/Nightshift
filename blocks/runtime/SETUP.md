# runtime — setup (written for a stranger)

Goal: the Nightshift loop runs in a Superserve microVM, not on a laptop. One command deploys;
`pause`/`resume` prove state survives; the dashboard gets a public URL judges can open.

## 0. One-time account work (no card needed)

1. Sign up at https://superserve.ai and grab `SUPERSERVE_API_KEY` (`ss_live_…`) from the console.
2. In the console → **Secrets**, create two secrets (this is where real values live — never here):
   - name `anthropic-key`, provider **Anthropic**, value = the company's Anthropic API key
   - name `stripe-key`, value = the company's Stripe restricted key
   The VM will see stand-in tokens, never these values.
3. Export the control-plane key in your shell: `export SUPERSERVE_API_KEY=ss_live_…`

## 1. Deploy

```bash
python3 blocks/runtime/code/runtime.py deploy
# → sandbox created: <id>
# → repo cloned, supervisor started
# → dashboard: https://8787-<id>.sandbox.superserve.ai
```

Options: `--repo` / `--branch` (what the VM clones), `--anthropic-secret` / `--stripe-secret`
(Superserve secret NAMES if you named them differently), `--state` (state-file path).

The state file (`code/.superserve-state.json`, git-ignored, 0600) holds the sandbox id and its
access token. Treat it like a key.

## 2. Drive it

```bash
python3 blocks/runtime/code/runtime.py status --json   # status + dashboard URL
python3 blocks/runtime/code/runtime.py exec --cmd "tail -20 /home/user/supervisor.log"
python3 blocks/runtime/code/runtime.py pull            # mirror state files to code/mirror/ (demo backup)
python3 blocks/runtime/code/runtime.py pause           # checkpoint the whole VM, stop billing
python3 blocks/runtime/code/runtime.py resume          # restore exactly where it left off
python3 blocks/runtime/code/runtime.py kill --yes      # delete everything (asks unless --yes)
```

## 3. The US-1.4 verification (do this once, on record)

1. `exec --cmd` an `add_task.py … --question "…"` so a `waiting_owner` task exists.
2. `pause` — the company is now a checkpoint on disk. Close the laptop if you like.
3. `resume` — within one supervisor cycle (default 120s) the approver answers it and the
   ledger gains a line. That is "the loop leaves the laptop", demonstrated.

## What runs inside the VM (supervisor.sh, every cycle)

dashboard (kept alive, port 8787, bound 0.0.0.0 for the preview URL) → approver pass
(`run-approver.sh`, skips empty queues without a model call) → taskrunner pass
(`tick-taskrunner.sh`, consumes answered questions, never invents answers) → sale recorder
(`record_sales.py`, idempotent). Stop it from outside with
`exec --cmd "rm /home/user/nightshift/.runtime.on"`.

## Fallback

If provisioning fails on demo day: laptop runtime as before (`start-taskrunner.sh` + cron'd
`run-approver.sh`) and say so on stage. Nothing in this block modifies the laptop path.
