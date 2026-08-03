# Acme Flows — brain routing hub

> This file governs how any agent reads and updates this Company Brain. It routes; it does not
> restate the whole business. Built with Project Sunday on 2026-08-03.
> ⚠️ Fictional example. Names and numbers are invented.

## Start reflex (every session)
1. **Read** `main_brain.md`, then the `main.md` of the entity you're working on.
2. **Act** (autonomy is broad — see the safety floor below).
3. **Document**: update that `main.md`'s "State as of `YYYY-MM-DD`" block + one dated line in
   `logs/YYYY-MM.md`.

## Where things live
| Need | File |
|---|---|
| General context (Acme Flows, founder, offer) | `main_brain.md` |
| The company itself | `acme/main.md` |
| A client (dental practice) | `clients/<practice>/main.md` |
| A project | `<owner>/projects/<project>/main.md` |
| People | the `notes/people.md` of the owning entity |
| Not-yet-owned | `misc/` |

## Core rules
- Three-subfolder structure per entity (`main.md` + `notes/` + `docs/` + `logs/`, `projects/` for the
  company and clients). Current state in `main.md`; history in `logs/` (monthly, append-only, not read
  by default).
- Ownership: every project belongs to someone. No `projects/` at the root. `misc/` = not-yet-owned.
- Read a person's `people.md` entry before writing to or about them; update it after.
- kebab-case; `YYYY-MM-DD`; source + date on facts; never a secret in a file; new automations start in
  review mode.

## Safety floor — always get an explicit human yes before:
- sending external emails (especially bulk) or any message that commits money or contract;
- publishing anything publicly in Acme Flows' name;
- writing to a client's production system (a practice's booking/records software);
- moving money, making payments, or entering financial/credential data;
- mass deletion, `git push --force`, `reset --hard`, or any hard-to-undo operation.

Everything else — research, drafting, analysis, brain files — proceed on your own.
