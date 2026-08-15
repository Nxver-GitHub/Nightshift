# Founding interview — create a company

> This is the heart of Nightshift. You're not filling a form; you're helping a founder think their
> business into existence, and capturing it as you go. Run it conversationally.

## How to run it (read first)

- **One question at a time.** Follow the phases in order, but let the conversation breathe.
- **Draft, then confirm.** As soon as you can infer something, propose it: *"So your ICP is
  independent physios in Belgium — right?"* Let them sharpen it. This is faster and better than
  interrogating.
- **Capture their words.** When a founder says something sharp about why they'll win, keep it
  verbatim in `positioning.md`. Polished summaries lose the edge.
- **Write as you go, or in batches.** You can create files after each phase, or hold and write at
  the end — but don't lose answers. If a phase runs long, checkpoint to disk.
- **"Good enough beats perfect."** It's fine to mark something *assumption — to confirm* and move on.
- **Depth scales with the founder.** A side-project needs 15 minutes; a serious venture warrants the
  full pass. Read the room.

Each phase below lists what to ask and **what it produces** in the brain.

---

## Phase 0 — Framing
Ask: the company's **name** (and derive a kebab-case **slug**); a **one-line** description of what it
does; the **working language**; and how the founder likes an assistant to communicate (direct?
formal? detail level?).
→ Produces: `main_brain.md` header, `CLAUDE.md` language/style, the brain folder name.

## Phase 1 — Identity & offer  *(spend the most time here)*
Ask, in order, but flow naturally:
1. **The problem** — what pain are you solving, and for whom? Why is it worth paying to fix?
2. **The customer (ICP)** — who *exactly* is the first customer? Push for narrow. "Everyone" is a
   red flag; help them cut.
3. **The offer** — what does the customer actually buy? How is it packaged? What's *out* of scope?
4. **Pricing model** — fixed price / subscription / usage / retainer? Rough number if they have one.
5. **Why you win** — why does the customer pick you over the alternative (including "do nothing")?
6. **Anti-position** — what will you deliberately *not* do? (This sharpens the brand.)
→ Produces: `{{company}}/notes/positioning.md` (their words), and the "State as of" seed.

## Phase 2 — Business model & first milestones
Ask:
1. **How money flows** — who pays, how often, what triggers a payment.
2. **Unit sanity** — rough cost to deliver one unit vs price; is there margin? (Mark assumptions.)
3. **The next three milestones** — the concrete things that must be true in the next weeks/months
   (first paying client, legal entity, first hire, MVP shipped…).
→ Produces: `{{company}}/main.md` → Context + Next steps; economics notes if substantial.

## Phase 3 — People & roles
Ask:
1. **Founder(s)** — name, role, what they want to keep doing themselves vs delegate.
2. **Anyone already involved** — cofounder, contractor, advisor, a first prospect who's a person.
3. **Which roles could be AI agents** — sales outreach, inbox triage, bookkeeping prep, content?
   (This is the Nightshift thesis: some roles are agents from day one. Note candidates; don't build them
   now — that's the next layer.)
→ Produces: `{{company}}/notes/people.md` (one entry each, with "how to talk to them"), and a note of
agent-role candidates in `positioning.md` or a `roles.md`.

## Phase 4 — Tools & operations
Ask what's **already set up** vs **to create**, across the usual surfaces: email/domain, CRM or
pipeline, accounting/invoicing, hosting/website, payments, calendar, storage. For each: what it's
for, who owns the account. **Do not collect passwords** — only where the credential lives.
→ Produces: `{{company}}/notes/tools.md`.

## Phase 5 — First clients & go-to-market
Ask:
1. **Known prospects** — any real names/companies already in reach? (Each real person → a
   `people.md` entry; each real prospect → the start of a `clients/` folder or a note.)
2. **The path to the first 3 clients** — how will they realistically land the first handful?
   Warm network? A channel? An offer hook?
→ Produces: seeds under `clients/` (or a `misc/pipeline.md` if too early), and Next steps.

## Phase 6 — Cadence & wrap
Ask:
1. **What to track** — the 1–3 numbers that tell them the business is working.
2. **Review rhythm** — when will they step back and look (weekly? on demand?).
Then move to `START-HERE.md` Step 3+ (choose location, scaffold, seed history, git, wrap up).
→ Produces: the "State as of" block, the first `logs/` line, and the finished tree.

---

## What "done" looks like
A brain matching `examples/acme-brain/`: a filled `main_brain.md`, a company `main.md` with a live
State block and 3 owned next steps, `positioning.md` in the founder's voice, `people.md` for everyone
named, `tools.md` split into in-place vs to-set-up, an empty-but-ready `clients/`, and a first dated
log line. The founder should be able to open Claude Code in that folder tomorrow and have any agent
be immediately useful.
