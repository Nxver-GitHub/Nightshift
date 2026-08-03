#!/bin/bash
# One headless email-operator run: triage today's inbox, prepare drafts, delegate multi-step work to
# the taskrunner. Never sends, deploys, or does anything irreversible — drafts + report only.
# Pair with the scheduled-tasks block to run this every N minutes, or call it by hand.
#
# Config (env): OPERATOR_DIR (default: this folder) · OPERATOR_MODEL (default: claude-opus-5)
OP_DIR="${OPERATOR_DIR:-$(cd "$(dirname "$0")" && pwd)}"
MODEL="${OPERATOR_MODEL:-claude-opus-5}"
LOG="$OP_DIR/operator.log"

echo "=== run $(date '+%Y-%m-%d %H:%M') ===" >> "$LOG"
claude -p "Run the email operator: load and follow the email-operator skill. Process only today's messages not already in state.json (mark each handled). Prepare drafts and delegate any multi-step work to the taskrunner with the message reference. Do NOT send, deploy, or do anything irreversible — drafts + report only." \
  --model "$MODEL" >> "$LOG" 2>&1
echo "=== end $(date '+%H:%M') ===" >> "$LOG"
