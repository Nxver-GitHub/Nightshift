#!/bin/bash
# Clean stop: remove the on/off flag. The loop finishes its current tick, then the launcher exits
# (it never kills a session mid-work). Same switch the dashboard's Stop button uses.
TR_DIR="${TASKRUNNER_DIR:-$(cd "$(dirname "$0")" && pwd)}"
rm -f "$TR_DIR/.taskrunner.on"
echo "[taskrunner] stop flag removed — the loop will finish its current tick and exit."
