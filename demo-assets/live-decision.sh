#!/bin/bash
# Put one real question through the gate, live, while the dashboard is on screen.
#
# The audit trail is the pitch, and a static ledger invites "when was that generated?". This asks
# the approver something the company genuinely faces, lets it decide against the written policy,
# and the decision appears on the dashboard within 15 seconds because the page re-reads on a timer.
#
# The question is deliberately one the policy CAN decide (a reprice inside P4's $5-25 band), so
# nothing escalates and no money moves while an audience is watching. Change --text if you want a
# different one, but read the clause first: ask something P9 doesn't cover and it will escalate,
# which is honest but is not the beat you want mid-demo.
#
# Usage:  bash demo-assets/live-decision.sh
set -euo pipefail
cd "$(dirname "$0")/.."

set -a; source .env; set +a

# run-approver.sh shells out to `claude`, which is NOT on PATH when Claude Code runs as the VS Code
# extension: the binary lives inside the extension bundle. Without this the pass fails with
# "claude: command not found", the question stays unanswered, and the board is left with a parked
# task that no agent is working — which looks exactly like the failure we are claiming not to have.
if ! command -v claude >/dev/null 2>&1; then
  CLAUDE_BIN=$(find "$HOME/.vscode/extensions" -maxdepth 4 -type f -name claude \
                 -path "*anthropic.claude-code*/resources/native-binary/*" 2>/dev/null | sort -V | tail -1)
  if [ -n "$CLAUDE_BIN" ]; then
    export PATH="$(dirname "$CLAUDE_BIN"):$PATH"
    echo "0/3  using the bundled CLI at $CLAUDE_BIN"
  else
    echo "ERROR: no 'claude' on PATH and none found in the VS Code extension bundle." >&2
    echo "       The approver cannot run, so this script would only park a task. Aborting." >&2
    exit 1
  fi
fi

export TASKRUNNER_TASKS="${TASKRUNNER_TASKS:-blocks/taskrunner/code/tasks.json}"
export APPROVER_POLICY="${APPROVER_POLICY:-company/nightshift/notes/policy.md}"
export APPROVER_LEDGER="${APPROVER_LEDGER:-blocks/approver/code/decisions.jsonl}"

QUESTION="May Nightshift reprice the Policy Gate Kit from \$19 to \$24 for the rest of today to test price sensitivity? This is a repricing of the existing listed product, not a new offer."

echo "1/3  creating the task…"
python3 blocks/taskrunner/code/add_task.py \
  --title "Reprice the Policy Gate Kit to \$24 for a price-sensitivity test" \
  --priority high --tasks "$TASKRUNNER_TASKS" >/dev/null

TASK_ID=$(python3 -c "
import json
print(json.load(open('$TASKRUNNER_TASKS'))['tasks'][-1]['id'])")

echo "2/3  asking the owner (task $TASK_ID) — watch it hit 'Waiting on owner'…"
python3 blocks/taskrunner/code/update_task.py \
  --id "$TASK_ID" --question "$QUESTION" --tasks "$TASKRUNNER_TASKS" >/dev/null
sleep 16   # one dashboard refresh cycle, so the audience sees it land in the column first

echo "3/3  running the approver — it reads the policy and answers…"
bash blocks/approver/code/run-approver.sh

echo
echo "Done. The decision is on the ledger; the dashboard picks it up within 15s."
python3 blocks/approver/code/approve.py log --limit 1
