#!/usr/bin/env python3
"""
study — one bounded general-population study, bought under the same money rules as everything else.

The labor block buys individual judgment (labor.py); this buys AGGREGATE judgment: n verified
humans answer one A/B question with one sentence of reasoning each. Built for the guidebook's
requirement that real human input measurably improves the project, with a clear before and after.

The money discipline is identical to a hire, deliberately:
  * The whole study is ONE outgoing spend, gated by the same P2 ceiling through --auth. No
    splitting a study into per-participant "actions" to duck the ceiling — the ledger sums
    actions, so an action must be the real economic unit.
  * Terac prices the draft; if the price exceeds the authorization, the draft is deleted and the
    next smaller participant count is tried (the "shrink ladder"). Unpriced = over-priced.
  * The decision rule is REGISTERED AT LAUNCH, in the study record, before any result exists:
    deploy the leading line only if completed >= min_n and margin >= min_margin; otherwise keep
    the incumbent and record "insufficient signal". Pre-registration is what makes the tally an
    evaluation rather than a vibe.

State: studies.jsonl next to this script (append-only, committed — it is evidence, like the
decision ledger). Reuses labor.py's transport/config so there is exactly one Terac chokepoint.

Usage:  python3 study.py <command>
  launch --line-a TEXT --line-b TEXT --auth USD [--participants 10] [--ladder 7,5]
  status [--json]                     votes so far on the latest launched study
  tally  [--min-n 5] [--margin 2]     apply the registered rule, approve completions, record
"""
import argparse
import datetime
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("labor", os.path.join(HERE, "labor.py"))
labor = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("labor", labor)
_spec.loader.exec_module(labor)

STUDIES = os.environ.get("LABOR_STUDIES", os.path.join(HERE, "studies.jsonl"))
# A vote is a screening answer, so any submission that got past screening carries one.
# screened_out (declined to reason / failed screen), rejected and abandoned carry none we trust.
VOTE_STATUSES = ("screen_passed", "in_progress", "awaiting_review", "approved")


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def read_studies() -> list:
    try:
        return [json.loads(x) for x in open(STUDIES, encoding="utf-8") if x.strip()]
    except (OSError, ValueError):
        return []


def append_study(entry: dict) -> None:
    with open(STUDIES, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def latest_launched() -> dict:
    for e in reversed(read_studies()):
        if e.get("kind") == "launch":
            return e
    raise labor.LaborError("no launched study on record — run `study.py launch` first.")


# ── launch ────────────────────────────────────────────────────────────────────
def build_payload(line_a: str, line_b: str, n: int, project_id: str) -> dict:
    return {
        "title": "60-second opinion: which product line would make you click?",
        "internal_title": "pitch A/B — Policy Gate Kit tagline",
        "description": (
            "Nightshift sells a $19 digital product for startup founders: a ready-made rulebook "
            "that lets an AI assistant approve routine business decisions safely.\n\n"
            "You'll answer two quick questions: which one-line pitch would make you more likely "
            "to click through to the product page, and one sentence on why. Your sentence enters "
            "the company's public research record verbatim — plain words are perfect.\n\n"
            "Then open the linked page for context and complete the task step."),
        "project_id": project_id,
        "num_participants": n,
        "business_type": "b2c",                      # general population, their fastest fill
        "unrestricted_audience": True,
        "expected_days_to_complete": 5,              # API minimum; fills far faster in practice
        "tasks": [{"sequence": 1, "task_type": "interview",
                   "review_type": os.environ.get("TERAC_REVIEW_TYPE", "auto_approve"),
                   "task_url": os.environ.get("TERAC_TASK_URL", labor.TERAC_TASK_URL_DEFAULT),
                   "duration_minutes": 3}],
        "screening_questions": [
            {"key": "pick",
             "text": "Which line would make you MORE likely to click through to the product?",
             "pick": "one",
             "answers": [{"text": line_a, "qualify_logic": "may"},
                         {"text": line_b, "qualify_logic": "may"}]},
            {"key": "why",
             "text": "In one sentence: why that one?",
             "pick": "one",
             "answers": [{"text": labor.TERAC_REASONING_OPT, "qualify_logic": "must_one_of",
                          "allow_free_text": True},
                         {"text": labor.TERAC_REASONING_DECLINE, "qualify_logic": "reject"}]},
        ],
    }


def cmd_launch(a: argparse.Namespace) -> int:
    auth = labor.parse_cost(a.auth)
    ceiling = labor.parse_ceiling()
    if auth > ceiling:
        raise labor.LaborError(
            f"--auth ${labor.fmt_usd(auth)} exceeds the policy's per-action ceiling "
            f"${labor.fmt_usd(ceiling)} (P2). A study is one spend; it obeys the same clause.")
    line_a, line_b = a.line_a.strip(), a.line_b.strip()
    if not line_a or not line_b or line_a == line_b:
        raise labor.LaborError("--line-a and --line-b must be two different non-empty lines.")
    leak = labor._LEAKY_RE.search(f"{line_a}\n{line_b}")
    if leak:
        raise labor.LaborError("a line contains something credential- or email-shaped — refusing "
                               "to broadcast it. Redact and relaunch.")

    ladder = [int(a.participants)] + [int(x) for x in a.ladder.split(",") if x.strip()]
    project_id = labor._terac_project_id()
    tried = []
    for n in ladder:
        draft = labor._terac_request("POST", "/opportunities",
                                     build_payload(line_a, line_b, n, project_id))
        oid = draft.get("id")
        cents = (draft.get("pricing") or {}).get("total_cost_cents")
        priced = None if cents is None else cents / 100.0
        if oid and priced is not None and priced <= auth:
            labor._terac_request("POST", f"/opportunities/{oid}/launch")
            entry = {"ts": now(), "kind": "launch", "study": "pitch-ab-1",
                     "opportunity_id": oid, "participants": n,
                     "authorized_usd": auth, "priced_usd": priced,
                     "line_a": line_a, "line_b": line_b,
                     # The rule, registered before any result exists:
                     "rule": {"min_n": 5, "min_margin": 2,
                              "on_insufficient": "keep incumbent (line_a)"}}
            append_study(entry)
            print(f"STUDY LIVE — {n} participants at ${labor.fmt_usd(priced)} "
                  f"(authorized ${labor.fmt_usd(auth)}), opportunity {oid}. "
                  f"Tally with: study.py tally")
            return 0
        tried.append(f"n={n}: {'unpriced' if priced is None else f'${labor.fmt_usd(priced)}'}")
        if oid:
            try:
                labor._terac_request("DELETE", f"/opportunities/{oid}")
            except labor.LaborError as e:
                print(f"WARNING: over-priced draft {oid} not deleted ({e}) — remove it in the "
                      f"dashboard.", file=sys.stderr)
    raise labor.LaborError(
        f"no rung of the ladder fits under ${labor.fmt_usd(auth)} ({'; '.join(tried)}). "
        f"Nothing launched, nothing spent.")


# ── status / tally ────────────────────────────────────────────────────────────
def fetch_votes(study: dict) -> dict:
    subs = labor._terac_request(
        "GET", f"/opportunities/{study['opportunity_id']}/submissions").get("data") or []
    votes, whys, pending_approval = {study["line_a"]: 0, study["line_b"]: 0}, [], []
    counted = 0
    for s in subs:
        if s.get("status") not in VOTE_STATUSES:
            continue
        answers = {x.get("key"): x.get("answer") or [] for x in s.get("screening_answers") or []}
        pick = next((str(v).strip() for v in answers.get("pick", []) if str(v).strip()), None)
        if pick not in votes:
            continue                      # no readable vote — not counted, not approved by tally
        votes[pick] += 1
        counted += 1
        labels = {labor.TERAC_REASONING_OPT.lower(), labor.TERAC_REASONING_DECLINE.lower()}
        why = " ".join(str(v).strip() for v in answers.get("why", [])
                       if str(v).strip() and str(v).strip().lower() not in labels)
        if why:
            whys.append({"pick": pick, "why": labor.sanitize_text(why, 300)})
        if s.get("status") == "awaiting_review":
            pending_approval.append(s["id"])
    return {"submissions": len(subs), "counted": counted, "votes": votes, "whys": whys,
            "pending_approval": pending_approval}


def cmd_status(a: argparse.Namespace) -> int:
    study = latest_launched()
    r = fetch_votes(study)
    out = {"opportunity_id": study["opportunity_id"], "participants": study["participants"],
           "counted": r["counted"], "votes": r["votes"], "whys": r["whys"]}
    print(json.dumps(out, ensure_ascii=False, indent=2) if a.json else
          f"{r['counted']}/{study['participants']} counted — " +
          " vs ".join(f"{v}" for v in r["votes"].values()))
    return 0


def cmd_tally(a: argparse.Namespace) -> int:
    study = latest_launched()
    if any(e.get("kind") == "tally" and e.get("opportunity_id") == study["opportunity_id"]
           for e in read_studies()):
        raise labor.LaborError("this study is already tallied — the registered rule runs once.")
    r = fetch_votes(study)
    a_votes, b_votes = r["votes"][study["line_a"]], r["votes"][study["line_b"]]
    rule = study.get("rule") or {"min_n": a.min_n, "min_margin": a.margin}

    if r["counted"] >= rule["min_n"] and abs(a_votes - b_votes) >= rule["min_margin"]:
        winner = study["line_a"] if a_votes > b_votes else study["line_b"]
        decision = "deploy_winner"
    else:
        winner = study["line_a"]          # the incumbent
        decision = "insufficient_signal_keep_incumbent"

    # Approve completed submissions — releasing payment is part of tallying, not an afterthought.
    for sid in r["pending_approval"]:
        labor._terac_request("POST", f"/submissions/{sid}/approve")

    entry = {"ts": now(), "kind": "tally", "opportunity_id": study["opportunity_id"],
             "counted": r["counted"], "votes": {"line_a": a_votes, "line_b": b_votes},
             "decision": decision, "winning_line": winner, "whys": r["whys"],
             "approved_submissions": len(r["pending_approval"])}
    append_study(entry)
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="One bounded general-population study on Terac.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("launch")
    s.add_argument("--line-a", required=True, help="the incumbent line (kept on any weak result)")
    s.add_argument("--line-b", required=True)
    s.add_argument("--auth", required=True, help="total authorization in dollars — one P2 action")
    s.add_argument("--participants", default="10")
    s.add_argument("--ladder", default="7,5", help="fallback participant counts, comma-separated")
    s.set_defaults(f=cmd_launch)
    s = sub.add_parser("status")
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_status)
    s = sub.add_parser("tally")
    s.add_argument("--min-n", type=int, default=5)
    s.add_argument("--margin", type=int, default=2)
    s.set_defaults(f=cmd_tally)
    return ap


def main(argv=None) -> None:
    a = build_parser().parse_args(argv)
    try:
        sys.exit(a.f(a))
    except labor.LaborError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
