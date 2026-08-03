# Content agents — install & operate

> For the founder's Claude Code agent. One session per network.

## Install
1. Copy `code/` into `command-center/content/`.
2. Set `CONTENT_STORE` (default `content.json` next to the script).
3. Install the skill once: `mkdir -p ~/.claude/skills/content-agent && cp blocks/content-agents/skill/content-agent.md ~/.claude/skills/content-agent/SKILL.md`,
   and set `$CONTENT` (content.py) inside it.

## Operate — one session per network
- Open a dedicated Claude Code session per network and set `$NETWORK` (linkedin | x | shorts | blog).
  Load `/content-agent`. Run it persistently (reuse the `taskrunner` block's `start-*.sh` pattern) or
  by hand.
- Flow: the agent proposes ideas and drafts (in the owner's voice), moves them to `ready`; **the
  owner posts by hand** and returns the URL → `content.py mark-posted --id N --url …`; later the
  agent records stats and iterates.

## Calibrate the voice
Give the agent a few of the owner's real posts up front so it writes as the owner, not as a brand.
Keep the best-performing drafts as references in the brain.

## Safety
No auto-posting, ever. The owner is the only publisher. No credentials in the brain.
