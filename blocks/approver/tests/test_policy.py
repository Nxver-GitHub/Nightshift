"""Structural tests for the written policy (US-0.2).

Deterministic only: these tests prove the policy FILE is sound — parseable caps, unique clause
IDs, prose/frontmatter agreement, hard NOs present, eval table consistent. Whether the approver
REASONS correctly against it is LLM behavior, exercised by the headless eval pass documented in
SETUP.md (seed the eval_cases questions into a scratch kanban, run run-approver.sh, diff the
ledger against expected_verdict) — not by pytest.
"""
import json
import re
from pathlib import Path

import pytest

BLOCK = Path(__file__).resolve().parent.parent
POLICY = BLOCK / "policy" / "policy.md"
EVAL = Path(__file__).resolve().parent / "eval_cases.jsonl"


def parse_frontmatter(text: str) -> dict:
    """Flat `key: value` frontmatter between --- fences; stdlib only (no yaml dep, repo idiom)."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "policy.md must start with a --- frontmatter block"
    out = {}
    for line in m.group(1).splitlines():
        key, _, val = line.partition(":")
        out[key.strip()] = val.strip()
    return out


@pytest.fixture(scope="module")
def text() -> str:
    return POLICY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def fm(text: str) -> dict:
    return parse_frontmatter(text)


@pytest.fixture(scope="module")
def clause_ids(text: str) -> list:
    return re.findall(r"\*\*(P\d+)\*\*", text)


def test_caps_parse_and_are_sane(fm):
    per_action = int(fm["per_action_spend_ceiling_usd"])
    daily = int(fm["daily_spend_cap_usd"])
    floor, ceiling = int(fm["price_floor_usd"]), int(fm["price_ceiling_usd"])
    # The caps must nest: one action can't blow the day, the floor can't cross the ceiling.
    assert per_action <= daily
    assert floor < ceiling
    assert int(fm["outbound_daily_cap"]) > 0
    assert int(fm["outbound_max_touches_per_contact"]) >= 1
    assert int(fm["outbound_followup_min_days"]) >= 1


def test_clause_ids_unique_and_contiguous(clause_ids):
    assert clause_ids, "no **Pn** clauses found"
    assert len(clause_ids) == len(set(clause_ids)), f"duplicate clause ids: {clause_ids}"
    nums = sorted(int(c[1:]) for c in clause_ids)
    # Contiguous from 1 so a ledger citation like [policy: P7] can never point at a gap.
    assert nums == list(range(1, len(nums) + 1)), f"clause numbering has gaps: {nums}"


def test_prose_matches_frontmatter_numbers(text, fm):
    # The frontmatter is what tools read; the prose is what the LLM reads. They must agree.
    assert f"${fm['per_action_spend_ceiling_usd']}" in text
    assert f"${fm['daily_spend_cap_usd']}" in text
    assert f"${fm['price_floor_usd']}–${fm['price_ceiling_usd']}" in text
    assert f"{fm['outbound_daily_cap']} sends" in text
    assert f"{fm['outbound_max_touches_per_contact']} touches" in text


def test_finalize_types_enumerated(text, fm):
    declared = [t.strip() for t in fm["approvable_finalize_types"].split(",")]
    # Must cover exactly update_task.py's gate types minus 'other' (which escalates by P8).
    assert sorted(declared) == sorted(["push", "email", "deploy", "archive"])
    for t in declared:
        assert f"`{t}`" in text, f"finalize type {t} declared but never addressed in prose"


def test_hard_nos_present(text):
    p10 = text[text.index("**P10**"):]
    for phrase in ("impersonate", "secret", "bypass", "ledger"):
        assert phrase in p10, f"hard-NO section is missing the '{phrase}' line"


def test_silence_is_never_consent(text):
    # The single most important sentence in the file — the escalation default.
    assert "Silence is never consent" in text


def test_eval_cases_parse_and_cite_real_clauses(clause_ids):
    cases = [json.loads(l) for l in EVAL.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(cases) >= 10
    valid = set(clause_ids)
    verdicts = set()
    for c in cases:
        assert c["expected_verdict"] in ("approve", "reject", "escalate")
        verdicts.add(c["expected_verdict"])
        for ref in c["expected_clauses"]:
            assert ref in valid, f"eval case cites {ref}, which is not a clause in policy.md"
    # The table must exercise all three verdicts or the eval proves nothing about escalation.
    assert verdicts == {"approve", "reject", "escalate"}
