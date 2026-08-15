# Nightshift — brain routing hub

> **Committed inside the kit repo deliberately — synthetic agent-founded company, no secrets; real
> brains live in sibling folders.** (`START-HERE.md` Step 3 puts a founder's brain in
> `../<company>-brain/`; this one is the hackathon's own agent-founded company and is meant to be
> read by judges, so it ships with the kit.)
>
> This file governs how any agent reads and updates this Company Brain. It routes; it does not
> restate the whole business. Built with the Nightshift kit on 2026-08-14.

## Start reflex (every session)
1. **Read** `main_brain.md` (general context), then the `main.md` of the entity you're working on.
2. **Act** (autonomy is broad — see the safety floor below).
3. **Document**: update that `main.md`'s "State as of `YYYY-MM-DD`" block + one dated line in
   `logs/YYYY-MM.md`.

## Where things live
| Need | File |
|---|---|
| General context (Nightshift, the founder-agent, the offer) | `main_brain.md` |
| The company itself (identity, model, positioning) | `nightshift/main.md` |
| **The operating law — every yes/no cites it** | `nightshift/notes/policy.md` |
| Positioning, ICP, offer, riskiest assumption | `nightshift/notes/positioning.md` |
| Roles and who does what (all agents) | `nightshift/notes/people.md` |
| Tools, rails, credential *names* | `nightshift/notes/tools.md` |
| History | `nightshift/logs/YYYY-MM.md` (append-only, not read by default) |
| A customer who becomes a real relationship | `clients/<client>/main.md` (create on first real buyer) |
| A project | `<owner>/projects/<project>/main.md` (create when one exists) |
| Anything without an owner yet | `misc/` (create when needed) |

`clients/`, `misc/`, `projects/` and `docs/` are **not created yet** — Nightshift is one day old and
has none. Create them the moment they have real content; never a folder ahead of its first fact.

## Core rules
- **Three-subfolder structure** per entity: `main.md` + `notes/` + `docs/` + `logs/` (+ `projects/`
  for the company and clients). Current state in `main.md`; history in `logs/` (one file per month,
  append-only, not read by default).
- **Ownership**: every project belongs to someone (a client, or the company). No `projects/` folder
  at the root. `misc/` is only for the not-yet-owned.
- **People first**: read the person's `people.md` entry before writing to or about them; update it
  after. Agent roles live in the same file — read the role before you act as it.
- **Conventions**: kebab-case names; `YYYY-MM-DD` dates; a source + date on every recorded fact;
  never a secret in a file; new automations start in review mode (prepare → human approves).
- **Cite the clause.** This company's gate is answered by the written policy in
  `nightshift/notes/policy.md`. Any approval, refusal, or escalation must name the clause (P1…P10).
  Silence in the policy is never consent — it escalates (P9).

## Safety floor — always get an explicit human yes before:
- sending external emails (especially bulk) or any message that commits money or contract;
- publishing anything publicly in Nightshift's name;
- writing to a client's production system;
- moving money, making payments, or entering financial/credential data;
- mass deletion, `git push --force`, `reset --hard`, or any hard-to-undo operation.

Everything else — research, drafting, analysis, creating/updating brain files — proceed on your own.

**How this company answers that floor.** Nightshift's whole thesis is that the "yes" above is given
by the **written policy** in `nightshift/notes/policy.md`, read by the approver agent, and recorded in
a decision ledger — not by removing the gate. The floor is unchanged; only who answers it changed.
Where the policy is silent, the answer is *escalate to a human* (P9) — and P10's hard NOs
(impersonation, exceeding caps, secrets in git, touching the gate or the policy itself) are never
approvable by anyone or anything.
