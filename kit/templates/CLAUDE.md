# {{COMPANY_NAME}} — brain routing hub

> This file governs how any agent reads and updates this Company Brain. It routes; it does not
> restate the whole business. Built with Project Sunday on {{DATE}}.

## Start reflex (every session)
1. **Read** `main_brain.md` (general context), then the `main.md` of the entity you're working on.
2. **Act** (autonomy is broad — see the safety floor below).
3. **Document**: update that `main.md`'s "State as of `YYYY-MM-DD`" block + one dated line in
   `logs/YYYY-MM.md`.

## Where things live
| Need | File |
|---|---|
| General context ({{COMPANY_NAME}}, founder, offer) | `main_brain.md` |
| The company itself (identity, model, positioning) | `{{COMPANY_SLUG}}/main.md` |
| A client | `clients/<client>/main.md` |
| A project | `<owner>/projects/<project>/main.md` |
| People (how to talk to them, contacts) | the `notes/people.md` of the owning entity |
| Anything without an owner yet | `misc/` |

## Core rules
- **Three-subfolder structure** per entity: `main.md` + `notes/` + `docs/` + `logs/` (+ `projects/`
  for the company and clients). Current state in `main.md`; history in `logs/` (one file per month,
  append-only, not read by default).
- **Ownership**: every project belongs to someone (a client, or the company). No `projects/` folder
  at the root. `misc/` is only for the not-yet-owned.
- **People first**: read the person's `people.md` entry before writing to or about them; update it after.
- **Conventions**: kebab-case names; `YYYY-MM-DD` dates; a source + date on every recorded fact;
  never a secret in a file; new automations start in review mode (prepare → human approves).

## Safety floor — always get an explicit human yes before:
- sending external emails (especially bulk) or any message that commits money or contract;
- publishing anything publicly in {{COMPANY_NAME}}'s name;
- writing to a client's production system;
- moving money, making payments, or entering financial/credential data;
- mass deletion, `git push --force`, `reset --hard`, or any hard-to-undo operation.

Everything else — research, drafting, analysis, creating/updating brain files — proceed on your own.
