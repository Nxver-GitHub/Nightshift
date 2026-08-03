#!/bin/bash
# Start the persistent TASKRUNNER session (kanban -> agents) in /loop, self-paced.
# Generalized from a working system. Around the loop: auto-relaunch if the session dies, an on/off
# flag (the Start/Stop switch), a PID-based anti-double-instance lock, and keep-awake.
#
# The loop starts on its own: the initial prompt "/loop /<skill>" is passed at launch (and on every
# relaunch). Nothing to type. Self-paced: it chains while a task is in progress, and spaces its
# wakeups when the kanban is empty. The skill carries the sentinel rule (never stop while the flag
# exists).
#
# Config (override via env):
#   TASKRUNNER_DIR      where this block lives         (default: this script's folder)
#   TASKRUNNER_SESSION  remote-control session name    (default: Taskrunner)
#   TASKRUNNER_MODEL    model for the session          (default: claude-opus-5)
#   TASKRUNNER_SKILL    installed skill name           (default: taskrunner)

TR_DIR="${TASKRUNNER_DIR:-$(cd "$(dirname "$0")" && pwd)}"
TR_SESSION="${TASKRUNNER_SESSION:-Taskrunner}"
TR_MODEL="${TASKRUNNER_MODEL:-claude-opus-5}"
TR_SKILL="${TASKRUNNER_SKILL:-taskrunner}"
FLAG="$TR_DIR/.taskrunner.on"
LOCK="$TR_DIR/.taskrunner.lock"

# ── Anti-double-instance (PID-based, checks the process is alive) ──────────────
# TWO taskrunners would claim the same task, delegate the same work twice, and write tasks.json at
# the same time. The lock carries the PID and we check it's ALIVE — otherwise a killed launcher would
# leave an eternal lock blocking every restart.
if [ -f "$LOCK" ]; then
  other=$(cat "$LOCK" 2>/dev/null)
  if [ -n "$other" ] && kill -0 "$other" 2>/dev/null; then
    echo "[taskrunner] a launcher is already running (PID $other) — this one exits, nothing touched."
    exit 0
  fi
  echo "[taskrunner] stale lock (PID $other gone) — taking over."
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

# ── keep-awake wrapper (macOS: caffeinate; elsewhere: no-op) ───────────────────
if command -v caffeinate >/dev/null 2>&1; then KEEPAWAKE="caffeinate -i"; else KEEPAWAKE=""; fi

touch "$FLAG"
echo "[taskrunner] started ($(date '+%Y-%m-%d %H:%M')). Stop with: ./stop-taskrunner.sh  (or rm '$FLAG')"

# ── auto-relaunch loop; the on/off flag is the kill switch ─────────────────────
while [ -f "$FLAG" ]; do
  start=$(date +%s)
  $KEEPAWAKE claude --remote-control "$TR_SESSION" \
    --model "$TR_MODEL" \
    --permission-mode auto \
    "/loop /$TR_SKILL"
  [ -f "$FLAG" ] || break
  dur=$(( $(date +%s) - start ))
  if [ "$dur" -lt 15 ]; then
    echo "[taskrunner] session exited in ${dur}s — likely a startup error (bad model/flag). Launcher stopped."
    break
  fi
  echo "[taskrunner] session ended $(date '+%H:%M') — relaunching in 10s (flag present)…"
  sleep 10
done
echo "[taskrunner] stopped."
