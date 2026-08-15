# Approver — install & operate

> For the founder's Claude Code agent. Requires the `taskrunner` block, already running.

## Install
1. Install `taskrunner` first. Note the path of its `tasks.json`.
2. Copy `code/` into `command-center/approver/`.
3. Wire the config (env vars — names here, values on the founder's machine only):
   - `TASKRUNNER_TASKS` — the taskrunner's kanban. Shared file, shared lock.
   - `APPROVER_POLICY` — the policy file you are about to write.
   - `APPROVER_LEDGER` — where decisions accumulate (default: `decisions.jsonl` next to `approve.py`).
4. Write the policy **with the founder**, not for them. Numbered clauses, one decision each, in the
   founder's own words. `policy/policy.md` is the reference policy (machine-readable caps in the
   frontmatter, prose clauses P1–P10 below — the two must agree, and `tests/test_policy.py` proves
   they do). Point `APPROVER_POLICY` at it, or at the founder's own copy installed into the brain
   at founding. A clause that doesn't say what is permitted, up to what limit, and for whom, is not
   a clause — it's a mood.
5. Install the skill:
   `mkdir -p ~/.claude/skills/approver && cp blocks/approver/skill/approver.md ~/.claude/skills/approver/SKILL.md`,
   then set `$AP` (the approver code dir) inside it.
6. `chmod +x code/run-approver.sh`.

## Verify it end-to-end (do this before trusting it)
1. Seed a question on a real card, using the taskrunner's own gate:
   ```bash
   python3 "$TR/update_task.py" --id <task-id> --question "May I refund 40 EUR to this client?"
   ```
   The task moves to `waiting_owner` — exactly as it would in production.
2. See it in the queue: `python3 approve.py pending` (and `--json` for the agent's view).
3. Run one pass: `./run-approver.sh` — or drive the skill by hand in a Claude Code session
   (`/approver`) the first few times, so the founder watches it reason.
4. Read the decision: `python3 approve.py log --limit 10`. Check the card too — `status` must still be
   `waiting_owner`, and only `question.answer` / `question.answered_at` may have changed.
5. Let the taskrunner pick it up. Its safety net consumes the answer on the next tick
   (`update_task.py --consume-question`) and the task resumes on its own. Nothing else to do.

## Operate
- **Cadence**: drive it with the `scheduled-tasks` block (every 15–30 min is plenty) or run
  `run-approver.sh` from cron. It exits without a model call when no question is waiting.
- **The ledger is the review surface**: read it weekly with the founder. Every escalation is a hole in
  the policy — either fill it with a new clause, or decide the hole is deliberate.
- **Tighten, don't loosen, after a surprise**: if an approve reads badly in hindsight, the fix is a
  clause, never a nudge to the skill.
- Run the tests after any change: `python3 -m pytest blocks/approver/tests/ -q`.

## Eval the reasoning (LLM behavior — separate from pytest)
The structural tests prove the policy file is sound; whether the agent *reasons* correctly against
it is checked by an eval pass over `tests/eval_cases.jsonl` (canned question → expected verdict +
clauses, all three verdicts covered):
1. Seed each case's question onto a task in a **scratch** kanban (`--tasks /tmp/eval-tasks.json`).
2. Run one approver pass over it (`run-approver.sh` with `TASKRUNNER_TASKS` pointed at the scratch file).
3. Diff `approve.py log --json` against each case's `expected_verdict` / `expected_clauses`.
Run it after any policy change; a mismatch means either the clause is ambiguous (rewrite the
clause) or the skill drifted (fix the skill). Never "fix" an eval by editing the expected verdict.

## Safety
The approver only ever answers questions — it never performs the action it approved; the taskrunner
still does, through the unchanged finalization gate. Escalations leave the task exactly as it was, so
the human-labor path can pick them up. Anything the policy is silent on is escalated, never assumed.
