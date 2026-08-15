# Labor — install & operate

> For the founder's Claude Code agent. Requires the `taskrunner` and `approver` blocks, already
> running. This block has no queue of its own — it reads the approver's escalations.

## Install
1. Install `taskrunner`, then `approver`. Note three paths: the kanban, the decision ledger, the
   policy file.
2. Copy `code/` into `command-center/labor/`.
3. Wire the config (env vars — names here, values on the founder's machine only):
   - `LABOR_PROVIDER` — `manual` (default) or `terac`. Start on `manual`.
   - `APPROVER_LEDGER` — the approver's `decisions.jsonl`. **The same file**, deliberately:
     escalations are read from it and human decisions are appended to it. Do not point this at a
     second ledger; two ledgers of decisions is how an audit trail stops being one.
   - `APPROVER_POLICY` — the written policy. Its frontmatter's `per_action_spend_ceiling_usd` is the
     hard cap on every hire. Without this file, the block refuses to hire at all.
   - `TASKRUNNER_TASKS` — the kanban shared with the taskrunner. Shared file, shared lock.
   - `LABOR_HIRES` — this block's own state (default: `hires.jsonl` next to `labor.py`).
   - `TERAC_API_KEY` — reserved for the terac driver. Environment only; never a file in this repo.

```bash
export LABOR_PROVIDER=manual
export TASKRUNNER_TASKS="$TR/tasks.json"
export APPROVER_LEDGER="$AP/decisions.jsonl"
export APPROVER_POLICY="$AP/../policy/policy.md"
export LABOR_HIRES="$LB/hires.jsonl"
```

## The drill — one hire, end to end, on the manual driver
Do this once before trusting it. It takes four minutes and it is also the demo.

1. **Seed an escalation.** Ask a question the policy genuinely cannot answer, through the
   taskrunner's own gate, then let the approver escalate it:
   ```bash
   python3 "$TR/update_task.py" --id <task-id> \
       --question "May I sign a 3-month retainer with this agency?"
   python3 "$AP/approve.py" escalate --id <task-id> \
       --reason "No clause covers a service engagement."
   ```
   The task stays `waiting_owner`, byte-identical. That is the designed outcome, not a failure.

2. **See the queue.** `python3 labor.py pending` (add `--json` for the agent's view). It lists only
   escalations whose task still carries an unanswered question and that no hire has answered yet.

3. **Open the hire.**
   ```bash
   python3 labor.py submit --id <task-id> --cost 12 \
       --context "EU agency, 3 months, ~$400/mo. Company sells digital products under $25."
   ```
   The task is not touched. The terminal prints the question, the context, and the exact command to
   come back with. Relay that block to any human expert you trust — Slack, phone, the person next to
   you. **The context is read by an outsider: treat it as public. No keys, no customer data.**

4. **Collect the judgment.** The expert returns one verdict and one paragraph:
   ```bash
   python3 labor.py collect --id <task-id> \
       --answer "approve: A 3-month retainer at this price is standard for the scope and stays inside the monthly budget."
   ```
   Anything that isn't `approve: …` or `reject: …` is refused rather than guessed — a misread verdict
   would write the wrong decision onto a live card.

5. **Check all three surfaces.**
   - The card: `question.answer` reads `APPROVED — … [via hired expert]`, `status` is still
     `waiting_owner`, one new journal line names the provider and the cost.
   - The ledger: `python3 "$AP/approve.py" log --limit 5` — the newest entry is `mode: "human"` with
     `cost_usd` and `provider`, sitting in the same file as the agent's own decisions. That contrast
     is the whole point; it is what you show a judge or an auditor.
   - The hire log: `python3 labor.py log` — the hire is now `answered`.

6. **Watch the taskrunner consume it.** On its next tick the runner picks the answer up
   (`update_task.py --consume-question`) and the task resumes on its own. Nothing else to do. The
   runner cannot tell a bought human from the founder — that is the drop-in claim, and
   `tests/test_labor.py` proves it against the real script.

## The ceiling
Every hire is checked against `per_action_spend_ceiling_usd` in the policy frontmatter **before**
anything is shown to an expert or written anywhere:

```bash
python3 labor.py submit --id <task-id> --cost 40
# ERROR: $40 exceeds the policy's per_action_spend_ceiling_usd of $15 (P2) — buying human
#        judgment obeys the same spend clause as every other payment. No hire opened.
```

Exit 1, no hire recorded, nothing relayed. If the founder wants to spend more per judgment, change
the clause **with them** and re-run — never bypass the gate, and never set a default in the code. If
`APPROVER_POLICY` is unset or the key is missing, the block refuses to hire rather than inventing a
ceiling nobody wrote.

## Operate
- **One open hire per escalation.** A second `submit` on the same task is refused until the first is
  collected. A judgment you dislike is still a judgment — escalations a hired human rejects stay
  rejected; do not re-hire around an answer.
- **Review the ledger weekly with the founder.** Every `mode: "human"` line is a hole in the policy
  that cost real money. Either write the clause that would have decided it, or agree the hole is
  deliberate and priced.
- **Cost shows up next to revenue.** The ledger carries `cost_usd` per hire; that is the number the
  dashboard/CRM reads as a cost event.
- Run the tests after any change: `uvx pytest blocks/labor/tests/ -q`.

## Tomorrow: filling in the terac driver
The `terac` driver is a structured stub. Both functions exit 1 with
`terac driver awaits TERAC_API_KEY + API docs (sponsor Slack, 8:30am) — structure ready, fill
submit/collect`, so nothing silently half-works.

Terac offers **two integration surfaces**; either fills the same two functions:
- **REST API** — call it directly from `labor.py` through one request helper, the way
  `blocks/payments/code/pay.py` keeps every HTTP call in a single `_request` chokepoint (so tests
  monkeypatch one symbol and stay offline). `submit` posts the question and returns a task ref;
  `collect` polls for the expert's verdict.
- **MCP** — let the labor skill call Terac's MCP tools in-session and hand the result back through
  `labor.py collect --id X --answer "<verdict>: <reasoning>"`. No new code path at all: the manual
  driver's parser already accepts exactly that shape.

To fill it in:
1. Get `TERAC_API_KEY` from the sponsor Slack at 8:30am and export it — environment only.
2. Read the current endpoint shapes from their docs. **Do not guess them**; the story is blocked on
   docs, not on code.
3. Replace `_terac_unavailable` with a real `terac_submit(task_id, question, context, cost)` and
   `terac_collect(task_id, answer, cost) -> (verdict, reasoning)` in `DRIVERS`. Everything after
   that — the money gate, the card write, the ledger entry, the hire log — is provider-independent
   and already done.
4. Store the provider's task reference on the hire entry if their API returns one; store nothing
   about the human. **No expert PII in any file.**
5. `manual` stays the permanent fallback. If Terac is slow or down during the demo, switch
   `LABOR_PROVIDER=manual` and the same drill works with a person in the room.

## Safety
The hired human is a substitute approver for one decision, never a worker: they answer, the
taskrunner still acts. Hires are capped by the policy's own spend ceiling. No expert PII is stored
anywhere. The context you send is read by an outsider — no secrets, no credentials, no customer data.
