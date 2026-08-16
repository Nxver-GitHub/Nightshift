"""Freeze the live ledgers into one static JSON the landing page renders from.

The page must never fetch from a running service at demo time: a surface that
depends on uptime is a surface that is blank in front of judges. This script is
run at freeze; the page reads only its output.

Redaction is deliberate. `recorded.jsonl` carries Stripe session and payment-link
identifiers, and this repo is public. Amounts and timestamps tell the whole story
without publishing anything that identifies a real buyer or a live payment object.
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
# The landing page now lives in the directory Render actually serves, alongside the storefront,
# so the snapshot has to land there too or the page renders yesterday's numbers.
OUT = ROOT / "blocks/storefront/site/data.json"

DECISIONS = ROOT / "blocks/approver/code/decisions.jsonl"
HIRES = ROOT / "blocks/labor/code/hires.jsonl"
SALES = ROOT / "blocks/payments/code/recorded.jsonl"


def read_jsonl(path):
    """Tolerate a missing or half-written ledger; a partial page beats a crash."""
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def clip(text, limit):
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def main():
    decisions = [
        {
            "ts": d.get("ts"),
            "task_id": d.get("task_id"),
            "question": clip(d.get("question"), 240),
            "verdict": d.get("verdict"),
            "reason": clip(d.get("reason"), 300),
            "clauses": d.get("policy_clauses_cited") or [],
            "mode": d.get("mode"),
        }
        for d in read_jsonl(DECISIONS)
    ]

    hires = [
        {
            "ts": h.get("ts"),
            "question": clip(h.get("question"), 240),
            "provider": h.get("provider"),
            "cost_usd": h.get("cost_usd"),
            "priced_usd": h.get("priced_usd"),
            "status": h.get("status"),
            "answer": clip(h.get("answer"), 420),
        }
        for h in read_jsonl(HIRES)
    ]

    # Amounts and timestamps only — no session_id, no link_id, no buyer data.
    sales = [
        {"ts": s.get("ts"), "amount_usd": s.get("amount_usd"), "status": s.get("status")}
        for s in read_jsonl(SALES)
    ]

    snapshot = {
        "generated_at": max([d["ts"] for d in decisions] + [s["ts"] for s in sales] + [""]),
        "totals": {
            "decisions": len(decisions),
            "human_approvals": 0,  # the claim: no owner ever stood behind a gate
            "escalations": sum(1 for d in decisions if d["verdict"] == "escalated"),
            "experts_hired": len(hires),
            # What actually left the company, not what was authorised. cost_usd is the ceiling the
            # approver signed off ($14); priced_usd is what Terac charged ($13.50). The ledger and
            # the deck both report the charge, so this has to agree with them.
            "labor_spend_usd": round(
                sum((h["priced_usd"] if h["priced_usd"] is not None else h["cost_usd"]) or 0
                    for h in hires), 2),
            "sales": len(sales),
            "revenue_usd": round(sum(s["amount_usd"] or 0 for s in sales), 2),
        },
        "decisions": decisions,
        "hires": hires,
        "sales": sales,
    }

    OUT.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    t = snapshot["totals"]
    print(
        f"data.json — {t['decisions']} decisions, {t['escalations']} escalated, "
        f"{t['experts_hired']} hires (${t['labor_spend_usd']}), "
        f"{t['sales']} sales (${t['revenue_usd']})"
    )


if __name__ == "__main__":
    main()
