"""
Deterministic tests for study.py — the shrink ladder, the pre-registered tally rule, and the
payment release. Transport-mocked like the terac driver tests: one symbol, no network.
"""
import importlib.util
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.join(os.path.dirname(HERE), "code")
POLICY = os.path.abspath(os.path.join(os.path.dirname(HERE), "..", "approver", "policy", "policy.md"))

_sspec = importlib.util.spec_from_file_location("study", os.path.join(CODE, "study.py"))
study = importlib.util.module_from_spec(_sspec)
sys.modules["study"] = study
_sspec.loader.exec_module(study)

LINE_A = "The written policy that answers your agent's approval queue while you sleep."
LINE_B = "The rules that make it safe to hand your agent the company card."


class Recorder:
    def __init__(self, responses):
        self.calls = []
        self.responses = responses

    def __call__(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        for (m, prefix), value in self.responses.items():
            if m == method and path.startswith(prefix):
                return value(payload) if callable(value) else value
        raise AssertionError(f"no canned response for {method} {path}")


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("APPROVER_POLICY", POLICY)
    monkeypatch.setattr(study, "STUDIES", str(tmp_path / "studies.jsonl"))
    monkeypatch.delenv("TERAC_API_KEY", raising=False)


def jsonl(path):
    if not os.path.exists(path):
        return []
    return [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]


def run(monkeypatch, rec, argv):
    monkeypatch.setattr(study.labor, "_terac_request", rec)
    with pytest.raises(SystemExit) as exc:
        study.main(argv)
    return exc.value.code


def launch_argv(auth="15"):
    return ["launch", "--line-a", LINE_A, "--line-b", LINE_B, "--auth", auth]


# ── launch: the shrink ladder ─────────────────────────────────────────────────
def test_launch_shrinks_until_the_price_fits(monkeypatch, capsys):
    """n=10 prices at $22 (deleted), n=7 at $14 (launched)."""
    ids = iter(["opp_10", "opp_7"])
    prices = {"opp_10": 2200, "opp_7": 1400}

    def create(payload):
        oid = next(ids)
        assert payload["business_type"] == "b2c"
        assert payload["unrestricted_audience"] is True
        assert [q["key"] for q in payload["screening_questions"]] == ["pick", "why"]
        assert [x["text"] for x in payload["screening_questions"][0]["answers"]] == [LINE_A, LINE_B]
        return {"id": oid, "pricing": {"total_cost_cents": prices[oid]}}

    rec = Recorder({
        ("GET", "/projects"): {"data": [{"id": "prj_1", "name": "Nightshift escalations"}]},
        ("POST", "/opportunities/opp_7/launch"): {},
        ("DELETE", "/opportunities/opp_10"): {},
        ("POST", "/opportunities"): create,
    })
    assert run(monkeypatch, rec, launch_argv()) == 0
    paths = [(m, p) for m, p, _ in rec.calls]
    assert ("DELETE", "/opportunities/opp_10") in paths
    assert ("POST", "/opportunities/opp_7/launch") in paths
    assert not any(p == "/opportunities/opp_10/launch" for _, p in paths)

    entry = jsonl(study.STUDIES)[0]
    assert entry["kind"] == "launch" and entry["participants"] == 7
    assert entry["priced_usd"] == 14.0 and entry["authorized_usd"] == 15.0
    assert entry["rule"] == {"min_n": 5, "min_margin": 2,
                             "on_insufficient": "keep incumbent (line_a)"}


def test_launch_refuses_when_no_rung_fits_and_spends_nothing(monkeypatch, capsys):
    ids = iter(["o1", "o2", "o3"])
    rec = Recorder({
        ("GET", "/projects"): {"data": [{"id": "prj_1", "name": "Nightshift escalations"}]},
        ("POST", "/opportunities"): lambda p: {"id": next(ids),
                                               "pricing": {"total_cost_cents": 9900}},
        ("DELETE", "/opportunities/"): {},
    })
    assert run(monkeypatch, rec, launch_argv()) == 1
    assert "nothing launched" in capsys.readouterr().err.lower()
    assert not any(p.endswith("/launch") for _, p, _ in rec.calls)
    assert [m for m, p, _ in rec.calls if m == "DELETE"] == ["DELETE"] * 3
    assert jsonl(study.STUDIES) == []


def test_launch_over_the_p2_ceiling_is_refused_before_any_call(monkeypatch, capsys):
    rec = Recorder({})
    assert run(monkeypatch, rec, launch_argv(auth="16")) == 1
    assert "P2" in capsys.readouterr().err
    assert rec.calls == []


# ── tally: the registered rule ────────────────────────────────────────────────
def seed_launch(participants=7):
    with open(study.STUDIES, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": "2026-08-15 12:40", "kind": "launch", "study": "pitch-ab-1",
            "opportunity_id": "opp_7", "participants": participants,
            "authorized_usd": 15.0, "priced_usd": 14.0,
            "line_a": LINE_A, "line_b": LINE_B,
            "rule": {"min_n": 5, "min_margin": 2,
                     "on_insufficient": "keep incumbent (line_a)"}}) + "\n")


def sub(sid, status, pick, why="Because it sounds safer."):
    return {"id": sid, "status": status, "screening_answers": [
        {"key": "pick", "answer": [pick]},
        {"key": "why", "answer": ["I will explain my reasoning here", why]}]}


def test_tally_deploys_the_winner_on_clear_signal_and_releases_payment(monkeypatch, capsys):
    seed_launch()
    subs = [sub(f"s{i}", "awaiting_review", LINE_B) for i in range(5)] + \
           [sub("s5", "approved", LINE_A), sub("s6", "screened_out", LINE_A)]
    rec = Recorder({
        ("GET", "/opportunities/opp_7/submissions"): {"data": subs},
        ("POST", "/submissions/"): {},
    })
    assert run(monkeypatch, rec, ["tally"]) == 0
    entry = jsonl(study.STUDIES)[-1]
    assert entry["kind"] == "tally"
    assert entry["votes"] == {"line_a": 1, "line_b": 5}      # screened_out never counts
    assert entry["decision"] == "deploy_winner" and entry["winning_line"] == LINE_B
    # Every awaiting_review completion was approved — tallying releases the payment.
    approvals = [p for m, p, _ in rec.calls if m == "POST" and p.startswith("/submissions/")]
    assert len(approvals) == 5


def test_tally_keeps_the_incumbent_on_thin_margin(monkeypatch):
    seed_launch()
    subs = [sub(f"s{i}", "approved", LINE_B) for i in range(4)] + \
           [sub(f"t{i}", "approved", LINE_A) for i in range(3)]
    rec = Recorder({("GET", "/opportunities/opp_7/submissions"): {"data": subs}})
    assert run(monkeypatch, rec, ["tally"]) == 0
    entry = jsonl(study.STUDIES)[-1]
    assert entry["decision"] == "insufficient_signal_keep_incumbent"    # 4-3: margin < 2
    assert entry["winning_line"] == LINE_A


def test_tally_keeps_the_incumbent_below_min_n(monkeypatch):
    seed_launch()
    subs = [sub("s0", "approved", LINE_B), sub("s1", "approved", LINE_B),
            sub("s2", "approved", LINE_B), sub("s3", "approved", LINE_B)]
    rec = Recorder({("GET", "/opportunities/opp_7/submissions"): {"data": subs}})
    assert run(monkeypatch, rec, ["tally"]) == 0
    entry = jsonl(study.STUDIES)[-1]
    assert entry["decision"] == "insufficient_signal_keep_incumbent"    # 4-0 but n < 5
    assert entry["counted"] == 4


def test_tally_runs_exactly_once(monkeypatch, capsys):
    seed_launch()
    rec = Recorder({("GET", "/opportunities/opp_7/submissions"):
                    {"data": [sub(f"s{i}", "approved", LINE_B) for i in range(6)]}})
    assert run(monkeypatch, rec, ["tally"]) == 0
    assert run(monkeypatch, rec, ["tally"]) == 1
    assert "already tallied" in capsys.readouterr().err
    assert sum(1 for e in jsonl(study.STUDIES) if e["kind"] == "tally") == 1
