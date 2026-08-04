# Project Sunday

**A kit that lets an AI agent build your company's "brain" — by interviewing you, not by making you fill in templates.**

<sub>**by [Meridiem](https://meridiem.be/en)** · created by Maxime Schifflers · repo: [github.com/MaxSch1/Project-Sunday](https://github.com/MaxSch1/Project-Sunday)</sub>

---

Sunday is a small, self-contained repository. You clone it, open it in
[Claude Code](https://claude.com/claude-code), and say `go`. From there an agent runs a
**founding interview** with you and generates a structured *Company Brain*: a set of Markdown
files that hold everything your business knows about itself — who you are, what you sell, who your
people are, what's happening — organized so that AI agents (and humans) can actually work from it.

It's the operating system behind a company that's run *with* AI agents, packaged so you can stand
up your own in an afternoon.

---

## Who it's for

- **Founders creating a new company.** This is the sweet spot. There's no legacy mess to clean up
  — Sunday gives your business a spine from day one.
- **Anyone who wants a real "second brain" for a project or a solo venture.** *(Personal mode is
  coming; today the kit is tuned for creating a company.)*

## What you get

Running Sunday produces a folder like this (names adapt to your business):

```
your-company-brain/
├── CLAUDE.md            ← routing rules: how any agent should read & update this brain
├── main_brain.md        ← the one-page context: your company, in a nutshell
├── company/
│   ├── main.md          ← identity, offer, positioning, business model
│   └── notes/           ← people.md, positioning.md, tools.md …
├── clients/             ← one folder per client, same shape, ready to fill
└── misc/                ← anything without an owner yet
```

Every entity follows the same rhythm: a `main.md` with a living **"State as of …"** block,
dated `logs/`, topic `notes/`, and a `people.md` you read *before* you write to someone.

## Two layers: brain, then blocks

Sunday installs in two layers:

1. **The brain** — memory and rules, built by the founding interview. Every business starts here.
2. **The blocks** — the working machinery: a dashboard, agents (inbox triage, task-runner,
   prospection…), connectors. Your agent consolidates the blocks *you* pick into your own private
   Command Center, wired to your tools. See [`blocks/`](blocks/).

Stop after the brain and add blocks later, or build the whole Command Center in one go.

## How to run it

1. Install [Claude Code](https://claude.com/claude-code).
2. Clone this repo and open it:
   ```bash
   git clone <this-repo-url> project-sunday && cd project-sunday
   claude
   ```
3. Type `go` (or `/sunday`) and answer the questions. The agent writes your brain into a **new,
   separate folder** next to this one — so this kit stays clean and you can pull updates later.

## What this repo does *not* contain

No real company data. Sunday ships the **method and the structure** — the rules, the templates,
the interview. Everything specific is generated live, from your answers, into your own folder.
The only company here is the fictional one in [`examples/`](examples/), to show you what "done"
looks like.

## Design principles

- **The interview is the product.** Templates alone become an abandoned empty skeleton. The value
  is an agent that asks the right questions and drafts from your answers.
- **Onboard a collaborator, don't install software.** The output is a brain a teammate could read
  and immediately be useful from.
- **A safety floor.** The generated brain tells agents what they may do on their own and what must
  wait for a human's explicit yes (sending money, publishing publicly, writing to production, mass
  emails, destructive git).
- **Plain Markdown + git.** No database, no lock-in. You own the files.

## Status

v0 — the create-a-company flow works end to end. Personal mode and agent "role" skills
(operator, task-runner, etc.) come next. See [`CHANGELOG.md`](CHANGELOG.md).

## License

_To be decided by the author before public release._
