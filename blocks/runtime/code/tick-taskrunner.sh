#!/bin/bash
# One headless pass of the taskrunner: work the kanban without a human or an interactive session.
# Mirrors run-approver.sh, because the dry run taught two lessons that MUST carry over:
#   1. Env vars do not reliably reach a `claude -p` session's tool shells — every path is passed
#      INSIDE the prompt as a command flag.
#   2. Permissions are scoped, never skipped: --allowedTools "Bash(python3 *)" means commands must
#      literally start with python3 to match.
#
# The interactive runtime (start-taskrunner.sh, /loop + remote-control) stays for the laptop; a
# supervised VM wants bounded passes it can retry, not a session it must babysit.
#
# Usage:  tick-taskrunner.sh [extra instruction]
# Config (names only — never echoed): TASKRUNNER_DIR · TASKRUNNER_MODEL (default claude-opus-5) ·
#         TASKRUNNER_TASKS (the kanban)
set -euo pipefail
DIR="${TASKRUNNER_DIR:-$(cd "$(dirname "$0")/../../taskrunner/code" && pwd)}"
MODEL="${TASKRUNNER_MODEL:-claude-opus-5}"
LOG="${TASKRUNNER_LOG:-$HOME/taskrunner-tick.log}"
TASKS="${TASKRUNNER_TASKS:-$DIR/tasks.json}"

# These paths are interpolated into the model prompt AND the permission patterns below. A quote
# or shell metacharacter in them would break both, so refuse loudly instead of running weird.
case "$DIR$TASKS$MODEL" in
  *"'"*|*'"'*|*'$'*|*'`'*|*';'*)
    echo "ERROR: TASKRUNNER_DIR/TASKRUNNER_TASKS/TASKRUNNER_MODEL contain shell metacharacters — refusing." >&2
    exit 1;;
esac

# Don't burn a model call on a quiet board: only tick when something is actionable —
# a todo task, or an in-progress/waiting task whose question has been answered.
# rc checked explicitly for the same reason as run-approver.sh: a broken kanban path must
# fail loudly here, not fall through into a paid model call.
ACTIONABLE=$(python3 - "$TASKS" <<'PY'
import json, sys
tasks = json.load(open(sys.argv[1])).get("tasks", [])
def ready(t):
    if t.get("status") == "todo":
        return True
    q = t.get("question") or {}
    return t.get("status") in ("in_progress", "waiting_owner") and q.get("answer")
print(sum(1 for t in tasks if ready(t)))
PY
) || {
  echo "ERROR: kanban unreadable at $TASKS — aborting before any model call." >&2
  echo "=== $(date '+%Y-%m-%d %H:%M') — ABORT: kanban check failed ===" >> "$LOG"
  exit 1
}
if [ "$ACTIONABLE" = "0" ]; then
  echo "=== $(date '+%Y-%m-%d %H:%M') — nothing actionable, skipped ===" >> "$LOG"
  exit 0
fi

echo "=== run $(date '+%Y-%m-%d %H:%M') — taskrunner tick ($ACTIONABLE actionable) ===" >> "$LOG"
# Trust boundary: "$*" reaches the model prompt verbatim — operator/cron input only, never
# third-party text. The gate stays intact headlessly: this pass may CONSUME answered questions
# but must never invent an answer (that is the approver's job, and only the approver's).
claude -p "Load and follow the taskrunner skill for ONE bounded pass over the kanban. Config for THIS pass — pass paths as FLAGS, never as env prefixes (commands must start with python3 for the permission rule to match): list with python3 '$DIR/list_tasks.py' --tasks '$TASKS' --json ; update with python3 '$DIR/update_task.py' --tasks '$TASKS' --id ... plus the relevant flags (--consume-question to consume an ANSWERED question, --status/--journal/--step to advance work, --question to raise a new owner question). Rules for this pass: work at most ONE task to its next state; NEVER write question.answer yourself — unanswered questions are the approver's; NEVER perform a finalize gesture unless its question carries an approved answer; journal every mutation. $*" \
  --model "$MODEL" \
  --allowedTools "Bash(python3 $DIR/list_tasks.py *)" "Bash(python3 $DIR/update_task.py *)" \
                 "Bash(python3 '$DIR/list_tasks.py' *)" "Bash(python3 '$DIR/update_task.py' *)" \
  >> "$LOG" 2>&1
# Scoped to the TWO scripts this pass may run — not to the python3 interpreter, which would be
# arbitrary code execution one prompt-injected task title away (security-review finding). Both
# quoting variants are allowed because a pattern miss doesn't fail safe: it strands the pass
# (the ba52a08 lesson), so we match the exact command shapes the prompt dictates.
echo "=== end $(date '+%H:%M') ===" >> "$LOG"
