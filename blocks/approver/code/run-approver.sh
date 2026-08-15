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

# Don't burn a model call on an empty queue: the kanban is usually fully answered.
# rc is checked EXPLICITLY — inside `[ $(...) ]`, set -e does not catch a failing substitution,
# and a broken config (missing kanban, bad TASKRUNNER_TASKS) must fail loudly here, not fall
# through into a paid model call.
PENDING=$(python3 "$DIR/approve.py" pending --json) || {
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
claude -p "Load and follow the approver skill for ONE pass over the pending owner questions. Read the policy file first; approve or reject only where a clause clearly applies, and escalate everything else. You answer questions only — never execute an approved action yourself. $*" \
  --model "$MODEL" >> "$LOG" 2>&1
echo "=== end $(date '+%H:%M') ===" >> "$LOG"
