# Scheduled tasks — install per OS

> For the founder's Claude Code agent. Runs any skill on a clock, review-mode first.

## 1. Place the runner
Copy `code/` into `command-center/scheduled-tasks/` and make the runner executable:
```bash
chmod +x command-center/scheduled-tasks/run-scheduled.sh
```
Test it once by hand: `./run-scheduled.sh email-operator` — check `scheduled-email-operator.log`.

## 2. Pick a scheduler and edit a template
All templates use `/ABS/PATH/...` placeholders — replace with real absolute paths.

- **cron (macOS/Linux)** — `templates/cron.txt`: `crontab -e`, paste an edited line.
- **launchd (macOS)** — `templates/launchd.plist`: edit label/paths, save to
  `~/Library/LaunchAgents/<label>.plist`, then `launchctl load ~/Library/LaunchAgents/<label>.plist`.
- **systemd (Linux)** — `templates/systemd.service` + `.timer`: save to `~/.config/systemd/user/`,
  then `systemctl --user enable --now <name>.timer`.

## 3. Keep it review-mode
The runner's prompt already tells the agent: prepare everything reversible, stop before anything
irreversible until a human confirms. Watch the logs for a few cycles. Only widen autonomy once a job
has proven it does the right thing.

## Notes
- The machine must be awake for a run to fire (a closed laptop skips it).
- Use this for periodic jobs (inbox triage, daily batches, health checks). For the always-on,
  reactive taskrunner, use its own persistent `/loop` launcher instead.
