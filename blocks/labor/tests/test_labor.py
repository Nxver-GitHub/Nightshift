"""
Deterministic tests for the labor block. No LLM, no network, no clock assumptions.

Two claims are under test:
  1. A hire is gated by the same money clause as every other spend (P2) — over the ceiling, nothing
     is printed to an expert and nothing is recorded.
  2. What a hired expert answers is indistinguishable, to the taskrunner, from what a human owner
     would have typed. The last test proves it by handing the answered card to the REAL
     `update_task.py --consume-question`.
"""
import json
import os
import subprocess
import sys
from typing import Any, Optional

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = os.path.dirname(HERE)
LABOR = os.path.join(BLOCK, "code", "labor.py")
UPDATE_TASK = os.path.abspath(
    os.path.join(BLOCK, "..", "taskrunner", "code", "update_task.py"))
POLICY = os.path.abspath(os.path.join(BLOCK, "..", "approver", "policy", "policy.md"))
CEILING = 15.0          # per_action_spend_ceiling_usd in the reference policy


def make_task(tid: str, status: str, question: Optional[dict] = None) -> dict:
    """A task exactly as add_task.py writes it, plus whatever update_task.py would have added."""
    return {
        "id": tid, "title": f"title {tid}", "description": "", "project": "", "due": "",
        "priority": "normal", "status": status, "claimed_by": None,
        "delegate_session_id": None, "email": None, "goal": None,
        "finalization": None, "journal": ["2026-08-14 09:00 — created by test"],
        "created_at": "2026-08-14 09:00", "started_at": None, "done_at": None,
        "question": question,
    }


def open_question(text: str = "May I sign a 3-month retainer with this agency?") -> dict:
    return {"text": text, "asked_at": "2026-08-14 10:00", "answer": None, "answered_at": None}


@pytest.fixture()
def kanban(tmp_path) -> Any:
    """One escalated task worth hiring for, plus decoys the queue must ignore."""
    tasks = [
        make_task("t-escalated", "waiting_owner", question=open_question()),
        make_task("t-answered", "waiting_owner",
                  question={"text": "Already handled?", "asked_at": "2026-08-14 08:00",
                            "answer": "APPROVED — by the owner", "answered_at": "2026-08-14 08:05"}),
        make_task("t-approved", "waiting_owner", question=open_question("May I refund 40 USD?")),
    ]
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps({"tasks": tasks}, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


@pytest.fixture()
def ledger(tmp_path) -> Any:
    """The approver's ledger as it would look after one escalation and two decoy entries."""
    entries = [
        # decoy: a decision the policy DID make — never a candidate for a hire
        {"ts": "2026-08-14 10:05", "task_id": "t-approved", "question": "May I refund 40 USD?",
         "verdict": "approve", "reason": "Refunds are unconditional.",
         "policy_clauses_cited": ["P5"], "mode": "agent"},
        {"ts": "2026-08-14 10:06", "task_id": "t-escalated",
         "question": "May I sign a 3-month retainer with this agency?", "verdict": "escalated",
         "reason": "No clause covers a service engagement.", "policy_clauses_cited": [],
         "mode": "agent"},
        # decoy: escalated, but its task was already answered by the owner
        {"ts": "2026-08-14 10:07", "task_id": "t-answered", "question": "Already handled?",
         "verdict": "escalated", "reason": "Policy silent.", "policy_clauses_cited": [],
         "mode": "agent"},
    ]
    path = tmp_path / "decisions.jsonl"
    path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
    return path


@pytest.fixture()
def hires(tmp_path) -> Any:
    return tmp_path / "hires.jsonl"


def run(args: list, kanban_path: Any, ledger_path: Any, hires_path: Any,
        provider: str = "manual", policy: Optional[str] = POLICY) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["APPROVER_LEDGER"] = str(ledger_path)
    env["LABOR_HIRES"] = str(hires_path)
    env["LABOR_PROVIDER"] = provider
    env.pop("TASKRUNNER_TASKS", None)   # --tasks must be what decides, not the ambient env
    env.pop("APPROVER_POLICY", None)
    env.pop("TERAC_API_KEY", None)      # a key in the developer's shell must not reach a test
    if policy:
        env["APPROVER_POLICY"] = policy
    scoped = args + (["--tasks", str(kanban_path)] if args[0] != "log" else [])
    return subprocess.run([sys.executable, LABOR] + scoped,
                          capture_output=True, text=True, env=env)


def read_task(kanban_path: Any, tid: str) -> dict:
    d = json.loads(kanban_path.read_text(encoding="utf-8"))
    return next(t for t in d["tasks"] if t["id"] == tid)


def jsonl(path: Any) -> list:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


# --- pending -----------------------------------------------------------------------------------

def test_pending_lists_only_the_open_escalation(kanban, ledger, hires):
    r = run(["pending", "--json"], kanban, ledger, hires)
    assert r.returncode == 0, r.stderr
    rows = json.loads(r.stdout)
    assert [x["id"] for x in rows] == ["t-escalated"]


def test_pending_row_shape(kanban, ledger, hires):
    rows = json.loads(run(["pending", "--json"], kanban, ledger, hires).stdout)
    row = rows[0]
    assert set(row) == {"id", "title", "question", "escalated_at", "escalation_reason",
                        "hire_status"}
    assert row["question"] == "May I sign a 3-month retainer with this agency?"
    assert row["escalation_reason"] == "No clause covers a service engagement."
    assert row["hire_status"] is None


def test_pending_human_output_names_only_the_escalation(kanban, ledger, hires):
    r = run(["pending"], kanban, ledger, hires)
    assert r.returncode == 0
    assert "t-escalated" in r.stdout
    assert "t-approved" not in r.stdout and "t-answered" not in r.stdout


def test_pending_warns_when_ledger_missing(kanban, tmp_path, hires):
    r = run(["pending", "--json"], kanban, tmp_path / "nope.jsonl", hires)
    assert r.returncode == 0
    assert "WARNING" in r.stderr
    assert json.loads(r.stdout) == []


def test_pending_warns_when_kanban_missing(tmp_path, ledger, hires):
    r = run(["pending", "--json"], tmp_path / "nokanban.json", ledger, hires)
    assert r.returncode == 0
    assert "WARNING" in r.stderr
    assert json.loads(r.stdout) == []


def test_pending_hides_an_escalation_already_answered_by_a_hire(kanban, ledger, hires):
    assert run(["submit", "--id", "t-escalated", "--cost", "10"],
               kanban, ledger, hires).returncode == 0
    assert run(["collect", "--id", "t-escalated", "--answer", "reject: A retainer is a service."],
               kanban, ledger, hires).returncode == 0
    assert json.loads(run(["pending", "--json"], kanban, ledger, hires).stdout) == []


def test_pending_flags_an_open_hire(kanban, ledger, hires):
    run(["submit", "--id", "t-escalated", "--cost", "10"], kanban, ledger, hires)
    rows = json.loads(run(["pending", "--json"], kanban, ledger, hires).stdout)
    assert rows[0]["hire_status"] == "submitted"


# --- submit: the money gate --------------------------------------------------------------------

def test_submit_under_the_ceiling_records_the_hire(kanban, ledger, hires):
    r = run(["submit", "--id", "t-escalated", "--cost", "12", "--context", "Agency is EU-based."],
            kanban, ledger, hires)
    assert r.returncode == 0, r.stderr
    entries = jsonl(hires)
    assert len(entries) == 1
    h = entries[0]
    assert set(h) == {"ts", "task_id", "question", "provider", "cost_usd", "status", "answer",
                      "answered_at"}
    assert h["task_id"] == "t-escalated"
    assert h["provider"] == "manual"
    assert h["cost_usd"] == 12.0
    assert h["status"] == "submitted"
    assert h["answer"] is None and h["answered_at"] is None
    assert h["question"] == "May I sign a 3-month retainer with this agency?"


def test_submit_leaves_the_task_untouched(kanban, ledger, hires):
    before = read_task(kanban, "t-escalated")
    run(["submit", "--id", "t-escalated", "--cost", "12"], kanban, ledger, hires)
    assert read_task(kanban, "t-escalated") == before


def test_submit_at_the_ceiling_exactly_is_allowed(kanban, ledger, hires):
    r = run(["submit", "--id", "t-escalated", "--cost", str(CEILING)], kanban, ledger, hires)
    assert r.returncode == 0, r.stderr
    assert len(jsonl(hires)) == 1


def test_submit_over_the_ceiling_is_refused_and_records_nothing(kanban, ledger, hires):
    r = run(["submit", "--id", "t-escalated", "--cost", "40"], kanban, ledger, hires)
    assert r.returncode == 1
    assert "per_action_spend_ceiling_usd" in r.stderr and "P2" in r.stderr
    assert jsonl(hires) == []
    assert "HIRE OPEN" not in r.stdout          # nothing was ever put in front of an expert


def test_submit_without_a_policy_refuses_rather_than_defaulting(kanban, ledger, hires):
    r = run(["submit", "--id", "t-escalated", "--cost", "1"], kanban, ledger, hires, policy=None)
    assert r.returncode == 1
    assert "APPROVER_POLICY" in r.stderr
    assert jsonl(hires) == []


@pytest.mark.parametrize("cost", ["0", "-5", "abc", ""])
def test_submit_rejects_a_nonsense_cost(kanban, ledger, hires, cost):
    r = run(["submit", "--id", "t-escalated", "--cost", cost], kanban, ledger, hires)
    assert r.returncode == 1
    assert jsonl(hires) == []


@pytest.mark.parametrize("tid", ["t-answered", "t-unknown"])
def test_submit_refuses_a_task_with_nothing_to_decide(kanban, ledger, hires, tid):
    r = run(["submit", "--id", tid, "--cost", "10"], kanban, ledger, hires)
    assert r.returncode == 1
    assert jsonl(hires) == []


def test_submit_refuses_a_second_open_hire(kanban, ledger, hires):
    run(["submit", "--id", "t-escalated", "--cost", "10"], kanban, ledger, hires)
    r = run(["submit", "--id", "t-escalated", "--cost", "10"], kanban, ledger, hires)
    assert r.returncode == 1
    assert len(jsonl(hires)) == 1


def test_submit_prints_the_relay_instructions(kanban, ledger, hires):
    r = run(["submit", "--id", "t-escalated", "--cost", "10", "--context", "Agency is EU-based."],
            kanban, ledger, hires)
    assert "May I sign a 3-month retainer" in r.stdout
    assert "Agency is EU-based." in r.stdout
    assert "collect --id t-escalated" in r.stdout


# --- collect: the round trip -------------------------------------------------------------------

@pytest.fixture()
def submitted(kanban, ledger, hires) -> Any:
    r = run(["submit", "--id", "t-escalated", "--cost", "12"], kanban, ledger, hires)
    assert r.returncode == 0, r.stderr
    return hires


def test_collect_writes_the_owner_fields_only(kanban, ledger, submitted):
    before = read_task(kanban, "t-escalated")
    r = run(["collect", "--id", "t-escalated",
             "--answer", "approve: A 3-month retainer is standard for this scope."],
            kanban, ledger, submitted)
    assert r.returncode == 0, r.stderr
    t = read_task(kanban, "t-escalated")
    assert t["question"]["answer"] == (
        "APPROVED — A 3-month retainer is standard for this scope. [via hired expert]")
    assert t["question"]["answered_at"]
    assert t["question"]["text"] == before["question"]["text"]
    assert t["question"]["asked_at"] == before["question"]["asked_at"]
    assert t["status"] == "waiting_owner"            # labor never moves the card
    assert len(t["journal"]) == len(before["journal"]) + 1
    assert "answered via hired human expert (manual, $12)" in t["journal"][-1]


def test_collect_reject_is_symmetric(kanban, ledger, submitted):
    r = run(["collect", "--id", "t-escalated", "--answer", "reject: Out of the fixed domain."],
            kanban, ledger, submitted)
    assert r.returncode == 0, r.stderr
    t = read_task(kanban, "t-escalated")
    assert t["question"]["answer"] == "REJECTED — Out of the fixed domain. [via hired expert]"
    assert t["status"] == "waiting_owner"


def test_collect_appends_a_human_ledger_entry(kanban, ledger, submitted):
    run(["collect", "--id", "t-escalated", "--answer", "approve: Standard for this scope."],
        kanban, ledger, submitted)
    entries = jsonl(ledger)
    assert len(entries) == 4                       # 3 seeded + 1 human decision
    e = entries[-1]
    assert e["task_id"] == "t-escalated"
    assert e["verdict"] == "approve"
    assert e["reason"] == "Standard for this scope."
    assert e["policy_clauses_cited"] == []
    assert e["mode"] == "human"
    assert e["cost_usd"] == 12.0
    assert e["provider"] == "manual"
    assert e["question"] == "May I sign a 3-month retainer with this agency?"
    assert e["ts"]


def test_collect_updates_the_hire_state(kanban, ledger, submitted):
    run(["collect", "--id", "t-escalated", "--answer", "approve: Standard for this scope."],
        kanban, ledger, submitted)
    entries = jsonl(submitted)
    assert len(entries) == 1
    assert entries[0]["status"] == "answered"
    assert entries[0]["answer"] == "approve: Standard for this scope."
    assert entries[0]["answered_at"]


def test_collect_leaves_other_tasks_untouched(kanban, ledger, submitted):
    before = json.loads(kanban.read_text(encoding="utf-8"))["tasks"]
    run(["collect", "--id", "t-escalated", "--answer", "approve: ok then."],
        kanban, ledger, submitted)
    after = json.loads(kanban.read_text(encoding="utf-8"))["tasks"]
    others = lambda ts: [t for t in ts if t["id"] != "t-escalated"]  # noqa: E731
    assert others(after) == others(before)


@pytest.mark.parametrize("answer", [
    "yes, go ahead",              # no verdict prefix at all
    "maybe: could go either way",  # unknown verdict
    "approve",                    # verdict, no separator
    "approve:   ",                # verdict, no reasoning
])
def test_collect_rejects_a_malformed_answer(kanban, ledger, submitted, answer):
    r = run(["collect", "--id", "t-escalated", "--answer", answer], kanban, ledger, submitted)
    assert r.returncode == 1
    assert r.stderr.strip()
    assert read_task(kanban, "t-escalated")["question"]["answer"] is None
    assert jsonl(submitted)[0]["status"] == "submitted"      # the hire stays open
    assert len(jsonl(ledger)) == 3                           # nothing added to the audit trail


def test_collect_without_an_answer_asks_for_one(kanban, ledger, submitted):
    r = run(["collect", "--id", "t-escalated"], kanban, ledger, submitted)
    assert r.returncode == 1
    assert "--answer" in r.stderr
    assert read_task(kanban, "t-escalated")["question"]["answer"] is None


def test_collect_without_an_open_hire_fails(kanban, ledger, hires):
    r = run(["collect", "--id", "t-escalated", "--answer", "approve: sure."],
            kanban, ledger, hires)
    assert r.returncode == 1
    assert read_task(kanban, "t-escalated")["question"]["answer"] is None
    assert len(jsonl(ledger)) == 3


def test_collect_does_not_overwrite_an_existing_answer(kanban, ledger, hires):
    """A hire opened before the owner answered by hand must not clobber the owner."""
    run(["submit", "--id", "t-escalated", "--cost", "10"], kanban, ledger, hires)
    d = json.loads(kanban.read_text(encoding="utf-8"))
    for t in d["tasks"]:
        if t["id"] == "t-escalated":
            t["question"]["answer"] = "REJECTED — by the owner"
            t["question"]["answered_at"] = "2026-08-14 11:00"
    kanban.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    r = run(["collect", "--id", "t-escalated", "--answer", "approve: sure."],
            kanban, ledger, hires)
    assert r.returncode == 1
    t = read_task(kanban, "t-escalated")
    assert t["question"]["answer"] == "REJECTED — by the owner"
    assert len(jsonl(ledger)) == 3


def test_collect_aborts_when_the_task_moved(kanban, ledger, hires):
    run(["submit", "--id", "t-escalated", "--cost", "10"], kanban, ledger, hires)
    d = json.loads(kanban.read_text(encoding="utf-8"))
    for t in d["tasks"]:
        if t["id"] == "t-escalated":
            t["status"] = "in_progress"
    kanban.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    r = run(["collect", "--id", "t-escalated", "--answer", "approve: sure."],
            kanban, ledger, hires)
    assert r.returncode == 2
    assert read_task(kanban, "t-escalated")["question"]["answer"] is None


# --- log ---------------------------------------------------------------------------------------

def test_log_dumps_the_hires(kanban, ledger, submitted):
    run(["collect", "--id", "t-escalated", "--answer", "approve: ok then."],
        kanban, ledger, submitted)
    entries = json.loads(run(["log", "--json"], kanban, ledger, submitted).stdout)
    assert [e["status"] for e in entries] == ["answered"]
    r = run(["log"], kanban, ledger, submitted)
    assert r.returncode == 0
    assert "t-escalated" in r.stdout and "$12" in r.stdout


def test_log_is_empty_without_hires(kanban, ledger, hires):
    r = run(["log", "--json"], kanban, ledger, hires)
    assert r.returncode == 0
    assert json.loads(r.stdout) == []


# --- drivers -----------------------------------------------------------------------------------

def test_terac_submit_without_key_fails_cleanly_and_records_nothing(kanban, ledger, hires):
    r = run(["submit", "--id", "t-escalated", "--cost", "10"], kanban, ledger, hires,
            provider="terac")
    assert r.returncode == 1
    assert "TERAC_API_KEY" in r.stderr
    assert jsonl(hires) == []
    assert read_task(kanban, "t-escalated")["question"]["answer"] is None


def test_terac_collect_rejects_a_manual_answer_flag(kanban, ledger, submitted):
    """--answer belongs to the manual driver; terac reads the answer from the API."""
    r = run(["collect", "--id", "t-escalated", "--answer", "approve: sure."],
            kanban, ledger, submitted, provider="terac")
    assert r.returncode == 1
    assert "--answer" in r.stderr
    assert read_task(kanban, "t-escalated")["question"]["answer"] is None
    assert jsonl(submitted)[0]["status"] == "submitted"
    assert len(jsonl(ledger)) == 3


def test_unknown_provider_fails_cleanly(kanban, ledger, hires):
    r = run(["submit", "--id", "t-escalated", "--cost", "10"], kanban, ledger, hires,
            provider="mechanical-turkey")
    assert r.returncode == 1
    assert "LABOR_PROVIDER" in r.stderr
    assert jsonl(hires) == []


# --- terac driver, transport-mocked ------------------------------------------------------------
# These run IN-PROCESS (importlib, like the payments/runtime suites) so the single network
# function `_terac_request` can be replaced. The claims: the documented call sequence, the price
# gate against Terac's OWN price, and that collect writes exactly what a human would have.
import importlib.util  # noqa: E402  (deliberately placed with the section that needs it)

_spec = importlib.util.spec_from_file_location("labor", LABOR)
labor = importlib.util.module_from_spec(_spec)
sys.modules["labor"] = labor
_spec.loader.exec_module(labor)


class TeracRecorder:
    """Stands in for labor._terac_request: records calls, replays canned responses by prefix."""

    def __init__(self, responses):
        self.calls = []
        self.responses = responses

    def __call__(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        for (m, prefix), value in self.responses.items():
            if m == method and path.startswith(prefix):
                return value
        raise AssertionError(f"no canned response for {method} {path}")


def terac_env(monkeypatch, kanban, ledger, hires):
    monkeypatch.setenv("APPROVER_LEDGER", str(ledger))
    monkeypatch.setenv("LABOR_HIRES", str(hires))
    monkeypatch.setenv("LABOR_PROVIDER", "terac")
    monkeypatch.setenv("APPROVER_POLICY", POLICY)
    monkeypatch.delenv("TASKRUNNER_TASKS", raising=False)


def run_inproc(monkeypatch, recorder, argv):
    monkeypatch.setattr(labor, "_terac_request", recorder)
    with pytest.raises(SystemExit) as exc:
        labor.main(argv)
    return exc.value.code


def submit_responses(price_cents=1200):
    return {
        ("GET", "/projects"): {"data": []},
        ("POST", "/projects"): {"id": "prj_1"},
        ("POST", "/opportunities/opp_1/launch"): {},
        ("POST", "/opportunities"): {"id": "opp_1",
                                     "pricing": {"total_cost_cents": price_cents}},
        ("DELETE", "/opportunities/opp_1"): {},
    }


def test_terac_submit_documented_sequence_and_shape(monkeypatch, kanban, ledger, hires, capsys):
    terac_env(monkeypatch, kanban, ledger, hires)
    rec = TeracRecorder(submit_responses())
    code = run_inproc(monkeypatch, rec,
                      ["submit", "--id", "t-escalated", "--cost", "14", "--tasks", str(kanban)])
    assert code == 0, capsys.readouterr().err

    assert [(m, p) for m, p, _ in rec.calls] == [
        ("GET", "/projects"), ("POST", "/projects"),
        ("POST", "/opportunities"), ("POST", "/opportunities/opp_1/launch")]
    body = rec.calls[2][2]
    assert body["project_id"] == "prj_1"
    assert body["num_participants"] == 1
    assert body["unrestricted_audience"] is True          # exactly one of filters/unrestricted
    assert "filters" not in body
    assert {q["key"] for q in body["screening_questions"]} == {"verdict", "reasoning"}
    verdict_q = next(q for q in body["screening_questions"] if q["key"] == "verdict")
    assert [a["text"] for a in verdict_q["answers"]] == ["Approve", "Reject"]
    assert body["expected_days_to_complete"] >= 5         # API minimum
    # The question the taskrunner asked reaches the expert verbatim.
    assert "May I sign a 3-month retainer with this agency?" in body["description"]

    hire = jsonl(hires)[0]
    assert hire["opportunity_id"] == "opp_1"
    assert hire["priced_usd"] == 12.0
    assert hire["status"] == "submitted"


def test_terac_submit_deletes_an_overpriced_draft_and_spends_nothing(
        monkeypatch, kanban, ledger, hires, capsys):
    terac_env(monkeypatch, kanban, ledger, hires)
    rec = TeracRecorder(submit_responses(price_cents=2500))   # $25 > authorized $14
    code = run_inproc(monkeypatch, rec,
                      ["submit", "--id", "t-escalated", "--cost", "14", "--tasks", str(kanban)])
    assert code == 1
    assert "draft deleted" in capsys.readouterr().err
    assert ("DELETE", "/opportunities/opp_1") in [(m, p) for m, p, _ in rec.calls]
    assert not any(p.endswith("/launch") for _, p, _ in rec.calls)
    assert jsonl(hires) == []                                  # no phantom open hire


def seed_terac_hire(hires):
    # authorized 14, actually priced 12 — the ledger must record what was CHARGED (review M1)
    hires.write_text(json.dumps({
        "ts": "2026-08-15 10:00", "task_id": "t-escalated",
        "question": "May I sign a 3-month retainer with this agency?", "provider": "terac",
        "cost_usd": 14.0, "status": "submitted", "answer": None, "answered_at": None,
        "opportunity_id": "opp_1", "priced_usd": 12.0}) + "\n", encoding="utf-8")


def test_terac_collect_writes_the_answer_and_releases_the_payout(
        monkeypatch, kanban, ledger, hires, capsys):
    terac_env(monkeypatch, kanban, ledger, hires)
    seed_terac_hire(hires)
    rec = TeracRecorder({
        ("GET", "/opportunities/opp_1/submissions"): {"data": [{
            "id": "s_1", "status": "awaiting_review",
            "screening_answers": [
                {"key": "verdict", "answer": ["Approve"]},
                {"key": "reasoning", "answer": ["My reasoning",
                                                "A 3-month retainer is standard for this scope."]},
            ]}]},
        ("POST", "/submissions/s_1/approve"): {},
    })
    code = run_inproc(monkeypatch, rec,
                      ["collect", "--id", "t-escalated", "--tasks", str(kanban)])
    assert code == 0, capsys.readouterr().err

    # Approving the submission is what releases the expert's payout.
    assert ("POST", "/submissions/s_1/approve") in [(m, p) for m, p, _ in rec.calls]
    q = read_task(kanban, "t-escalated")["question"]
    assert q["answer"] == ("APPROVED — A 3-month retainer is standard for this scope."
                           " [via hired expert]")
    entry = jsonl(ledger)[-1]
    assert entry["mode"] == "human" and entry["provider"] == "terac"
    assert entry["cost_usd"] == 12.0        # charged price, not the authorized 14 (review M1)
    assert jsonl(hires)[0]["status"] == "answered"


def test_terac_submit_refuses_to_broadcast_credentials_or_emails(monkeypatch):
    """The question goes verbatim to an unrestricted public audience — anything leaky is refused
    BEFORE the first network call (review H2)."""
    rec = TeracRecorder({})            # any call would raise "no canned response"
    monkeypatch.setattr(labor, "_terac_request", rec)
    for bad in ["ping our client at jane@acme.example about the renewal",
                "the stripe key rk_live_abc123 stopped working — replace it?"]:
        with pytest.raises(labor.LaborError) as exc:
            labor.terac_submit("t-x", bad, "", 10.0)
        assert "refusing to broadcast" in str(exc.value)
    assert rec.calls == []


def test_terac_collect_strips_ansi_from_the_experts_reasoning(
        monkeypatch, kanban, ledger, hires, capsys):
    """An outside human's words reach terminals, the dashboard, and a headless LLM — control
    sequences are stripped at the collect choke point (review M2/C1)."""
    terac_env(monkeypatch, kanban, ledger, hires)
    seed_terac_hire(hires)
    rec = TeracRecorder({
        ("GET", "/opportunities/opp_1/submissions"): {"data": [{
            "id": "s_1", "status": "approved",
            "screening_answers": [
                {"key": "verdict", "answer": ["Reject"]},
                {"key": "reasoning", "answer": ["\x1b[32mLooks APPROVED\x1b[0m to me\x07 — "
                                                "but the terms are unacceptable."]},
            ]}]},
    })
    code = run_inproc(monkeypatch, rec,
                      ["collect", "--id", "t-escalated", "--tasks", str(kanban)])
    assert code == 0, capsys.readouterr().err
    answer = read_task(kanban, "t-escalated")["question"]["answer"]
    assert "\x1b" not in answer and "\x07" not in answer
    assert answer.startswith("REJECTED — Looks APPROVED to me")   # words kept, escapes gone


def test_terac_collect_waits_when_the_expert_is_still_working(
        monkeypatch, kanban, ledger, hires, capsys):
    terac_env(monkeypatch, kanban, ledger, hires)
    seed_terac_hire(hires)
    rec = TeracRecorder({
        ("GET", "/opportunities/opp_1/submissions"): {"data": [{"id": "s_0",
                                                               "status": "in_progress"}]},
    })
    code = run_inproc(monkeypatch, rec,
                      ["collect", "--id", "t-escalated", "--tasks", str(kanban)])
    assert code == 1
    assert "still be working" in capsys.readouterr().err
    assert read_task(kanban, "t-escalated")["question"]["answer"] is None
    assert len(jsonl(ledger)) == 3                             # nothing appended
    assert jsonl(hires)[0]["status"] == "submitted"            # hire stays open


# --- integration: the drop-in claim ------------------------------------------------------------

def test_taskrunner_consumes_the_hired_experts_answer(kanban, ledger, submitted):
    """The real proof: the untouched taskrunner script accepts what a bought human wrote."""
    assert os.path.isfile(UPDATE_TASK), "the taskrunner block must be present"
    r = run(["collect", "--id", "t-escalated",
             "--answer", "approve: A 3-month retainer is standard for this scope."],
            kanban, ledger, submitted)
    assert r.returncode == 0, r.stderr

    consumed = subprocess.run(
        [sys.executable, UPDATE_TASK, "--id", "t-escalated", "--consume-question",
         "--tasks", str(kanban)], capture_output=True, text=True)
    assert consumed.returncode == 0, consumed.stderr

    t = read_task(kanban, "t-escalated")
    assert t["question"] is None                       # the Q/A was archived and cleared
    assert any("Q/A consumed" in line for line in t["journal"])
    assert any("via hired expert" in line for line in t["journal"])
