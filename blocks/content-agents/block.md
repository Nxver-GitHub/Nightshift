# content-agents

> One persistent agent per social network. It generates ideas, writes posts **in the owner's voice**
> (never a pitch), tracks their status, and reads stats to iterate — but it **never publishes**. The
> owner posts by hand and returns the URL. Generalized from a working set of per-network agents.

## What it gives you
A parameterized content-agent role (one skill, driven per network) plus a small tracker
(`content.py`) that moves items idea → draft → ready → posted and records stats. Run one session per
network (LinkedIn, X, shorts, blog); each keeps its own voice and cadence.

## What it needs
- **Tools / accounts**: Python 3, Claude Code (a persistent session per network), and a way to read
  each network's stats (its UI/analytics — via the browser, for example). No posting API is used.
- **Config the agent must fill**: `CONTENT_STORE` (content.json path), `NETWORK` per session.
- **Depends on blocks**: none. Reuses the `taskrunner` block's launcher pattern if you want the
  sessions kept alive; pairs with the `dashboard` to see the pipeline.

## What's in this block
- `code/content.py` + `code/content.json` — the per-network content pipeline (`add`, `set`,
  `mark-posted`, `stats`, `list`, `show`).
- `skill/content-agent.md` — the role, parameterized by `$NETWORK`: ideas → draft in the owner's
  voice → hand off to post → read stats → iterate. Never publishes.
- `SETUP.md` — install & operate (one session per network).

## v1 scope (honest)
Ships the pipeline and the role. It does **not** auto-post (by design) and doesn't fetch stats for
you — reading a network's analytics is left to the owner's tools (e.g. the browser). The persistent
"one session per network" run can reuse the `taskrunner` launcher pattern.

## Safety
The agent **never publishes** — posting publicly in the company's name is the owner's action, on the
brain's safety floor. It stores drafts and stats locally; no credentials in the brain.
