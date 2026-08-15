#!/bin/bash
# supervisor.sh — the company's heartbeat, running INSIDE the Superserve VM (US-1.4).
#
# Replaces start-taskrunner.sh as the runtime (not modified — that script stays for the laptop
# fallback). No caffeinate, no PID theatrics: the VM does not sleep, and pause/resume checkpoints
# this very process, so survival across restarts is the platform's job, not this script's.
#
# Each cycle, in order (order matters — answers must exist before the taskrunner consumes them):
#   1. dashboard  — ensure the read-only audit dashboard is serving (preview URL depends on it)
#   2. approver   — one headless pass over unanswered owner questions (run-approver.sh, proven)
#   3. taskrunner — one headless pass over the kanban (tick-taskrunner.sh, same pattern)
#   4. sales      — poll pay.py sales and record new ones in the CRM (idempotent, US-1.2)
#
# Config arrives as sandbox env vars set by runtime.py at create (NIGHTSHIFT_HOME, TASKRUNNER_TASKS,
# APPROVER_POLICY, APPROVER_LEDGER, CRM_DB, DASH_PORT, DASH_BIND). They survive pause/resume.
set -u
NS="${NIGHTSHIFT_HOME:?NIGHTSHIFT_HOME must be set (runtime.py deploy sets it)}"
INTERVAL="${SUPERVISOR_INTERVAL:-120}"   # seconds between cycles; the approver skips empty queues cheaply
FLAG="$NS/.runtime.on"

touch "$FLAG" && chmod 600 "$FLAG"   # the flag is the kill switch; owner-only
echo "[supervisor] started $(date '+%Y-%m-%d %H:%M') — stop with: rm $FLAG"

while [ -f "$FLAG" ]; do
  # 1. Dashboard: restart if dead. pgrep -f matches the exact server invocation.
  if ! pgrep -f "python3 $NS/blocks/dashboard/code/server.py" >/dev/null 2>&1; then
    nohup python3 "$NS/blocks/dashboard/code/server.py" >> "$HOME/dashboard.log" 2>&1 &
    echo "[supervisor] dashboard (re)started on :${DASH_PORT:-8787}"
  fi

  # 2. Approver: run-approver.sh exits 0 on an empty queue without a model call.
  bash "$NS/blocks/approver/code/run-approver.sh" \
    || echo "[supervisor] approver pass failed (exit $?) — next cycle retries"

  # 3. Taskrunner: one bounded pass; same headless discipline as the approver.
  bash "$NS/blocks/runtime/code/tick-taskrunner.sh" \
    || echo "[supervisor] taskrunner pass failed (exit $?) — next cycle retries"

  # 4. Sales -> CRM. record_sales is idempotent on session id, so re-runs are safe.
  python3 "$NS/blocks/payments/code/record_sales.py" run \
      --crm-db "${CRM_DB:-$NS/blocks/crm/code/crm.db}" \
      --state "$NS/blocks/payments/code/recorded.jsonl" \
    || echo "[supervisor] sales recording failed (exit $?) — next cycle retries"

  sleep "$INTERVAL"
done
echo "[supervisor] stopped (flag removed)."
