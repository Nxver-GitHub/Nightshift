# prospection

> Outbound that stays under control. A pipeline — watch for signals, qualify, find the contact,
> write a short email sequence, get it **validated by the owner**, send the approved batch, handle
> replies — all on top of the `crm` block's database. Generalized from a working system.

## What it gives you
A prospecting role (the skill) plus a small queue tool (`prospection.py`) that manages 3–4 step email
sequences with a hard **validation gate**: nothing is ever sent until the owner approves it. The
actual sending is done by the `email-operator` block (or whatever email tool the founder uses); this
block owns the *queue*, the *scripts*, and the *gate*.

## What it needs
- **Tools / accounts**: Python 3, the `crm` block (same SQLite database), and an email-sending path
  (the `email-operator` block or a mail connector). Optionally a way to find contacts (research).
- **Config the agent must fill**: `CRM_DB` (env) — the **same** database as the crm block.
- **Depends on blocks**: `crm` (required). Pairs with `email-operator` (to actually send) and
  `taskrunner` (to schedule the daily batch as a task).

## What's in this block
- `code/prospection.py` — sequences + steps on the CRM database: `create-sequence`, `add-step`,
  `submit`, `approve`, `due-today`, `mark-sent`, `reply-received`, `show`. Guards: no sequence to an
  opted-out contact; nothing sendable until approved.
- `skill/prospection.md` — the role: qualify → find contact → write the sequence from proven scripts
  → submit for the owner's yes → send the approved batch → handle replies.
- `SETUP.md` — install & operate.

## v1 scope (honest)
Ships the pipeline mechanics and the validation gate. It does **not** ship prospecting *scripts*
(the actual email copy) — those are yours to write; the skill explains how to build a small library
of proven ones. Signal-watching (finding whom to contact) is described in the skill but left to your
research tools; the block doesn't scrape anything.

## Safety
The gate is the whole point: `due-today` only ever lists **approved** steps, and the owner approves
before anything sends. Bulk sending and any message that commits are on the brain's safety floor —
route the actual send through the owner's yes (the `email-operator` finalization, or a manual approve).
