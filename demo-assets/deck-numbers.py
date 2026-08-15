#!/usr/bin/env python3
"""
Print every number the deck needs, in slide order, read from live state.

At 18:00 with a submission lock approaching, hunting through decisions.jsonl and crm.db by hand is
how a wrong figure ends up on a slide. This reads both and prints exactly the nine placeholders in
demo-assets/deck.html, plus the ones it CANNOT compute, said out loud rather than guessed.

Read-only. Never writes to the ledger or the CRM.

Usage:
    python3 demo-assets/deck-numbers.py
    python3 demo-assets/deck-numbers.py --ledger path/to/decisions.jsonl --crm path/to/crm.db

Config (env, same names the other blocks use):
    APPROVER_LEDGER    decisions.jsonl   (default: blocks/approver/code/decisions.jsonl)
    CRM_DB             crm.db            (default: blocks/crm/code/crm.db)
"""
import argparse
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_LEDGER = os.path.join(REPO, "blocks", "approver", "code", "decisions.jsonl")
DEFAULT_CRM = os.path.join(REPO, "blocks", "crm", "code", "crm.db")

# Stages that mean money actually landed. `won` is signed but not yet delivered; both count as
# revenue for the deck, and we print them apart so the split is a decision, not an accident.
PAID_STAGES = ("won", "delivered")


def read_ledger(path):
    """Returns (entries, malformed_count). A corrupt line is stepped over, exactly as the
    dashboard does, so this and the dashboard can never disagree about the totals."""
    if not os.path.exists(path):
        return None, 0
    entries, malformed = [], 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                malformed += 1
    return entries, malformed


def read_crm(path):
    if not os.path.exists(path):
        return None
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    marks = ",".join("?" * len(PAID_STAGES))
    rows = c.execute(
        f"SELECT stage, COUNT(*) n, COALESCE(SUM(amount),0) total "
        f"FROM projects WHERE stage IN ({marks}) GROUP BY stage", PAID_STAGES).fetchall()
    c.close()
    return {r["stage"]: {"n": r["n"], "total": r["total"]} for r in rows}


def line(label, value, note=""):
    print(f"  {label:<34} {value:<12} {note}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=os.environ.get("APPROVER_LEDGER") or DEFAULT_LEDGER)
    ap.add_argument("--crm", default=os.environ.get("CRM_DB") or DEFAULT_CRM)
    a = ap.parse_args()

    print("\nDECK NUMBERS  (demo-assets/deck.html)\n" + "=" * 66)

    # ── slide 5: the run ──────────────────────────────────────────────────────────────────────
    print("\nSLIDE 5 — the run")
    entries, malformed = read_ledger(a.ledger)
    if entries is None:
        print(f"  no ledger at {a.ledger}")
        print("  -> the run has not produced decisions yet. Both figures stay [FILL].")
    else:
        escalated = sum(1 for e in entries if e.get("verdict") == "escalated")
        human = [e for e in entries if e.get("mode") == "human"]
        cost = sum(float(e.get("cost_usd") or 0) for e in human)
        line("decisions in the run", len(entries))
        line("answered by an owner", 0, "hardcoded on the slide — must stay 0")
        line("escalated & bought", f"{escalated} / {len(human)}", "escalations / humans hired")
        line("spent on human judgment", f"${cost:.2f}", "for the spoken line on slide 4")
        if malformed:
            print(f"  NOTE: {malformed} unreadable ledger line(s) skipped.")
        if escalated and not human:
            print("  WARNING: escalations exist but no human answered one. Slide 4's story needs "
                  "at least one mode:\"human\" entry.")

    # ── slide 6: the money ────────────────────────────────────────────────────────────────────
    print("\nSLIDE 6 — the money")
    crm = read_crm(a.crm)
    if crm is None:
        print(f"  no CRM db at {a.crm}")
        print("  -> no sales recorded yet. Revenue and buyers stay [FILL].")
    else:
        buyers = sum(v["n"] for v in crm.values())
        revenue = sum(v["total"] for v in crm.values())
        line("revenue", f"${revenue:.0f}")
        line("buyers", buyers)
        for stage, v in sorted(crm.items()):
            line(f"  of which {stage}", f"{v['n']} (${v['total']:.0f})")
        if not buyers:
            print("  No sale has landed yet. This is the win condition — nothing else "
                  "substitutes for it.")

    # ── what this script deliberately will not invent ─────────────────────────────────────────
    print("\nCANNOT BE COMPUTED — you must supply these")
    line("strangers, not in this room", "[FILL]", "needs your sale-by-sale attribution")
    line("Terac panel size", "[FILL]", "from the study")
    line("disagreements, of ten", "[FILL]", "from the study")
    line("agreement before / after", "[FILL]", "from the study")
    print("\n  These four are judgement or study output. Guessing any of them puts an invented\n"
          "  number on a stage whose entire claim is that nothing here was faked.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
