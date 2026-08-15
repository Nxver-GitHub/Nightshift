#!/bin/bash
# One headless pass of the approver: answer the taskrunner's unanswered owner questions from the
# written policy. Point cron / launchd / systemd at this script, or run it by hand.
#
# Usage:  run-approver.sh [extra instruction]
# Config (names only — never echoed): APPROVER_DIR (default this folder) · APPROVER_MODEL
#         (default claude-opus-5) · TASKRUNNER_TASKS (the kanban) · APPROVER_POLICY (the clauses)
set -euo pipefail
DIR="${APPROVER_DIR:-$(cd "$(dirname "$0")" && pwd)}"
MODEL="${APPROVER_MODEL:-claude-opus-5}"
LOG="$DIR/approver.log"

# Resolve config HERE and pass it inside the prompt text. Env vars exported by the caller do
# NOT reliably reach a `claude -p` session's tool shells (they initialize fresh) — a dry run
# proved a headless pass silently saw an empty default kanban. Paths in the prompt are
# deterministic; env inheritance is not.
TASKS="${TASKRUNNER_TASKS:-$DIR/../../taskrunner/code/tasks.json}"
POLICY="${APPROVER_POLICY:?APPROVER_POLICY must be set — the approver cannot reason without the written policy}"
LEDGER="${APPROVER_LEDGER:-$DIR/decisions.jsonl}"

# Don't burn a model call on an empty queue: the kanban is usually fully answered.
# rc is checked EXPLICITLY — inside `[ $(...) ]`, set -e does not catch a failing substitution,
# and a broken config (missing kanban, bad TASKRUNNER_TASKS) must fail loudly here, not fall
# through into a paid model call.
PENDING=$(TASKRUNNER_TASKS="$TASKS" APPROVER_POLICY="$POLICY" python3 "$DIR/approve.py" pending --json) || {
  echo "ERROR: approve.py pending failed — check TASKRUNNER_TASKS / kanban path. Aborting before any model call." >&2
  echo "=== $(date '+%Y-%m-%d %H:%M') — ABORT: pending check failed ===" >> "$LOG"
  exit 1
}
if [ "$PENDING" = "[]" ]; then
  echo "=== $(date '+%Y-%m-%d %H:%M') — no pending questions, skipped ===" >> "$LOG"
  exit 0
fi

echo "=== run $(date '+%Y-%m-%d %H:%M') — approver ===" >> "$LOG"
# Trust boundary: "$*" is appended into the model prompt verbatim. Only a trusted operator or a
# fixed cron line may pass arguments — never route third-party text (emails, form input) in here.
claude -p "Load and follow the approver skill for ONE pass over the pending owner questions. Config for THIS pass — pass paths as FLAGS, never as env prefixes (commands must start with python3 for the permission rule to match): list with python3 '$DIR/approve.py' pending --tasks '$TASKS' --json ; decide with python3 '$DIR/approve.py' answer --tasks '$TASKS' --ledger '$LEDGER' --id ... --verdict ... --reason ... --policy-ref ... ; escalate with python3 '$DIR/approve.py' escalate --tasks '$TASKS' --ledger '$LEDGER' --id ... --reason ... — the policy file to read first is '$POLICY'. Approve or reject only where a clause clearly applies, and escalate everything else. You answer questions only — never execute an approved action yourself. $*" \
  --model "$MODEL" \
  --allowedTools "Bash(python3 $DIR/approve.py *)" "Bash(python3 '$DIR/approve.py' *)" \
  >> "$LOG" 2>&1
# Scoped to approve.py itself, not to the python3 interpreter (tightened after security review:
# "Bash(python3 *)" also matched `python3 -c ...`, i.e. arbitrary code one prompt-injected
# question away). Never --dangerously-skip-permissions. Both quoting variants are allowed
# because a pattern miss doesn't fail safe — it strands correct verdicts (the ba52a08 lesson).
# MUST be re-verified with a live headless pass before it next matters (14:00 spine re-run).
echo "=== end $(date '+%H:%M') ===" >> "$LOG"
