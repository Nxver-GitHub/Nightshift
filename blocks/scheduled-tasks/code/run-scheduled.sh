#!/bin/bash
# Generic scheduled runner: one headless Claude Code pass of a skill. Review-mode by default — the
# agent prepares everything reversible and stops before anything irreversible (a human approves).
# Point cron / launchd / systemd at this script. This is the PERIODIC complement to the taskrunner's
# persistent /loop session.
#
# Usage:  run-scheduled.sh <skill-name> [extra instruction]
# Config: SCHED_MODEL (default claude-opus-5) · SCHED_DIR (default this folder, for logs)
SKILL="$1"; shift; EXTRA="$*"
if [ -z "$SKILL" ]; then
  echo "usage: run-scheduled.sh <skill-name> [extra instruction]"; exit 1
fi
MODEL="${SCHED_MODEL:-claude-opus-5}"
DIR="${SCHED_DIR:-$(cd "$(dirname "$0")" && pwd)}"
LOG="$DIR/scheduled-$SKILL.log"

echo "=== run $(date '+%Y-%m-%d %H:%M') — $SKILL ===" >> "$LOG"
claude -p "Load and follow the $SKILL skill for one pass. $EXTRA Prepare everything reversible; do NOT send, deploy, or do anything irreversible without explicit human confirmation — this is a review-mode scheduled run." \
  --model "$MODEL" >> "$LOG" 2>&1
echo "=== end $(date '+%H:%M') ===" >> "$LOG"
