# The Company Brain — rules every brain obeys

> This is the method behind Project Sunday. It applies to any agent working inside a generated
> brain. It is deliberately small: a handful of rules that make a pile of Markdown behave like a
> memory a team can trust.

## The base reflex (every session)

1. **Read first:** `main_brain.md` (general context), then the `main.md` of the entity you're
   about to work on. Nothing else by default.
2. **Act.**
3. **Document after:** update that `main.md`'s **"State as of `YYYY-MM-DD`"** block, and append one
   dated line to `logs/YYYY-MM.md`.

If you only remember one thing: **the current state lives in `main.md`; the history lives in `logs/`.**

## Structure — the three-subfolder rule

Every client, project, or entity has the same shape:

```
<entity>/
├── main.md      ← the essentials + the "State as of" block + any structural quirks
├── notes/       ← one .md per topic: everything useful to an agent (people, positioning, tools…)
├── docs/        ← finished documents (contracts, offers, PDFs, decks…)
├── logs/        ← tracking of what was done. ONE FILE PER MONTH (YYYY-MM.md), short dated,
│                  append-only. Agents do NOT read logs/ by default — it's for looking back.
└── projects/    ← (clients and the company only) one subfolder per project, same shape.
```

## `main.md` — the discipline

- Standard sections: **Context · State as of · Contacts/Access · Links · Next steps**, with a
  **Last updated** date at the top.
- The **"State as of `YYYY-MM-DD`"** block is **3–5 lines, max**, rewritten on every meaningful
  action: where things stand, what's blocked, what's next. Raw detail goes to `logs/`, not here.
- **Next steps** carries concrete, dated, owned actions. **Nothing dormant:** an open item without
  a next action is a bug — give it one.

## People (`notes/people.md`)

- Anyone tied to an entity gets an entry in that entity's `notes/people.md` (one `##` section each).
- Same ownership rule as projects: a client's contact lives in the client's `people.md`; a
  vendor/partner of the company lives in the company's `people.md`. Someone spanning contexts: full
  entry in their main context, a one-line pointer elsewhere. Never duplicate.
- An entry holds: role/relationship, **how to talk to them** (register, tone, sensitivities), useful
  context, **contact details** on greppable lines, and the last dated interaction.
- **Read the entry before writing to or about the person; update it after any exchange that taught
  you something.**

## Ownership — routing with no ambiguity

- **Every project belongs to someone.** Client work → `clients/<client>/projects/<project>/`.
  No client → it's the company's → `<company>/projects/<project>/`.
- **There is no `projects/` folder at the root.** Never create one.
- A cross-client project lives with the client who owns the relationship; a one-line pointer file
  sits with the others. Never duplicate.
- `misc/` holds only what has no owner yet. The moment it becomes a project, move it.

## Root of the brain

- `main_brain.md` — general context (the company, the founder, the offer in a nutshell). The entry
  point for any new agent.
- `CLAUDE.md` — the routing hub: how to read and update this brain, where things live, and the
  safety floor. Loaded automatically by Claude Code at the brain's root.
- Top-level folders: `<company>/`, `clients/`, `misc/` (add a personal one only if you keep private
  life here — and if so, never load it by default).

## Writing conventions

- **kebab-case** for all files and folders (`acme-corp`, `first-offer.md`). No spaces, no parentheses.
- Dates are `YYYY-MM-DD`. **Put a source + date on every fact you record** (who said it, which site,
  which search). An unverified claim is marked *assumption — to confirm*.
- **Never write a secret, password, or token in a file.** Record *where* the credential lives, not
  its value.
- **Review mode:** every new automated workflow starts in "prepare, human approves" mode; it goes
  fully automatic only once it's proven.

## The safety floor (what always needs a human's explicit yes)

An agent may act on its own for research, drafting, analysis, and creating/updating brain files.
It must **stop and get an explicit yes before** anything irreversible or committing, including:

- sending external emails (especially in bulk) or any message that commits money or contract;
- publishing anything publicly in the company's name;
- writing to a client's production system;
- moving money, making payments, or entering financial/credential data;
- mass deletion, `git push --force`, `reset --hard`, or any hard-to-undo operation.

The generated `CLAUDE.md` must restate this floor so every future agent inherits it.

## Agents as roles (forward-looking)

Beyond files, a mature brain gains **role skills** — an operator that triages the inbox, a
task-runner that executes queued work, a prospector, and so on. Each is a named agent with one job,
reading the same brain. Sunday v0 sets up the memory; the role skills are the next layer.
