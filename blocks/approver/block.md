# approver

> The owner's-yes gate, **kept** — with an agent standing behind it. The taskrunner still stops
> before every irreversible gesture and still asks. What changes is who is available to answer at
> 3am. Zero modification to `taskrunner` or any other block.

## What it gives you
Your taskrunner already stops at the irreversible line and asks a question on the card. That question
sits there until you personally read it — which is where an otherwise autonomous company goes to
sleep. This block installs an **approver agent** that answers those questions from a policy *you*
wrote: it approves what a clause clearly permits, rejects what a clause clearly forbids, and escalates
everything else untouched for you. It writes exactly the two fields a human wrote (`question.answer`,
`question.answered_at`) into the same `tasks.json`, under the same lock — so the taskrunner cannot
tell the difference and needs no change at all. Every decision lands in an append-only ledger with the
clauses it cited: an audit trail you (or a reviewer) can read line by line.

## What it needs
- **Tools / accounts**: Python 3, Claude Code, and the `taskrunner` block already running.
- **Config the agent must fill**: `TASKRUNNER_TASKS` (the kanban it shares with the taskrunner),
  `APPROVER_POLICY` (path to the founder's written policy — numbered clauses `P1`, `P2`, …),
  `APPROVER_LEDGER` (path to the append-only decision log). Names only; no values, no secrets.
- **Depends on blocks**: `taskrunner` (required). Optionally driven by `scheduled-tasks`.

## What's in this block
- `code/approve.py` — the interface: `pending`, `answer`, `escalate`, `log`. Dumb plumbing — it never
  reads the policy and never decides; it writes the owner's two fields under the taskrunner's lock and
  records the decision.
- `code/run-approver.sh` — headless one-pass launcher; exits without a model call when the queue is empty.
- `skill/approver.md` — the role: read the policy, triage each question into approve / reject /
  escalate, cite clauses, never approve on silence.
- `tests/` — deterministic pytest suite, including a real `update_task.py --consume-question`
  round-trip proving the drop-in claim.
- `SETUP.md` — install & operate.

## How the agent installs it
1. Install `taskrunner` first and note its `tasks.json` path.
2. Copy `code/` into `command-center/approver/`.
3. Write the policy file with the founder (numbered clauses, one decision each) and point
   `APPROVER_POLICY` at it. Set `TASKRUNNER_TASKS` to the taskrunner's kanban and `APPROVER_LEDGER`
   to a writable path. Never hardcode a path or a secret into the scripts.
4. Install the skill into the founder's setup.
5. Start in review mode: run one pass by hand, read the ledger with the founder, and only then let
   `scheduled-tasks` drive it. See `SETUP.md`.

## Safety
- The approver **never executes an action**. It answers questions. The taskrunner still performs every
  gesture, after it consumes the answer — the gate is unchanged, only staffed.
- It writes **only** `question.answer` and `question.answered_at`. It never changes `status`, never
  edits the question text, never overwrites an answer a human already gave.
- **Escalation leaves the task byte-identical** — still `waiting_owner`, still unanswered, waiting for
  the human-labor path, which finds it in the ledger. Silence in the policy is never permission.
- **Irreversible actions** (`push`, `email`, `deploy`, `archive`) require an explicit clause match on
  that specific gesture and target. Never approved by inference, never half-approved.
- No secret ever goes into a reason, a card, or the ledger — the ledger is written to be read.
