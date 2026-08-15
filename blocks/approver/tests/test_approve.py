"""
Deterministic tests for the approver's interface. No LLM, no network, no clock assumptions.

The point of this suite is one claim: `approve.py answer` is indistinguishable from the human who
used to type into the card. The last test proves it by handing the answered task to the REAL
taskrunner script (`update_task.py --consume-question`) and checking it accepts it.
"""
import json
import os
import subprocess
import sys
from typing import Any, Optional

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = os.path.dirname(HERE)
APPROVE = os.path.join(BLOCK, "code", "approve.py")
UPDATE_TASK = os.path.abspath(
    os.path.join(BLOCK, "..", "taskrunner", "code", "update_task.py"))
POLICY = os.path.join(HERE, "fixture_policy.md")


def make_task(tid: str, status: str, question: Optional[dict] = None,
              finalization: Optional[dict] = None) -> dict:
    """A task exactly as add_task.py writes it, plus whatever update_task.py would have added."""
    return {
        "id": tid, "title": f"title {tid}", "description": "", "project": "", "due": "",
        "priority": "normal", "status": status, "claimed_by": None,
        "delegate_session_id": None, "email": None, "goal": None,
        "finalization": finalization, "journal": ["2026-08-14 09:00 — created by test"],
        "created_at": "2026-08-14 09:00", "started_at": None, "done_at": None,
        "question": question,
    }


def open_question(text: str = "May I refund 40 EUR?") -> dict:
    return {"text": text, "asked_at": "2026-08-14 10:00", "answer": None, "answered_at": None}


@pytest.fixture()
def kanban(tmp_path) -> Any:
    """One kanban covering every branch: answerable, answerable+irreversible, not waiting, answered."""
    tasks = [
        make_task("t-open", "waiting_owner", question=open_question()),
        make_task("t-finalize", "waiting_owner",
                  question=open_question("May I run these irreversible steps?\n- Push the code: main"),
                  finalization={"actions": [{"type": "push", "detail": "main", "done": False}],
                                "posted_at": "2026-08-14 10:00", "confirmed_at": None}),
        make_task("t-todo", "todo"),
        make_task("t-answered", "waiting_owner",
                  question={"text": "Already handled?", "asked_at": "2026-08-14 08:00",
                            "answer": "APPROVED — by the owner", "answered_at": "2026-08-14 08:05"}),
    ]
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps({"tasks": tasks}, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


@pytest.fixture()
def ledger(tmp_path) -> Any:
    return tmp_path / "decisions.jsonl"


def run(args: list, kanban_path: Any, ledger_path: Any) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["APPROVER_LEDGER"] = str(ledger_path)
    env["APPROVER_POLICY"] = POLICY
    env.pop("TASKRUNNER_TASKS", None)   # --tasks must be what decides, not the ambient env
    scoped = args + (["--tasks", str(kanban_path)] if args[0] != "log" else [])
    return subprocess.run([sys.executable, APPROVE] + scoped,
                          capture_output=True, text=True, env=env)


def read_task(kanban_path: Any, tid: str) -> dict:
    d = json.loads(kanban_path.read_text(encoding="utf-8"))
    return next(t for t in d["tasks"] if t["id"] == tid)


def ledger_lines(ledger_path: Any) -> list:
    if not ledger_path.exists():
        return []
    return [json.loads(x) for x in ledger_path.read_text(encoding="utf-8").splitlines() if x.strip()]


# --- pending -----------------------------------------------------------------------------------

def test_pending_lists_only_unanswered_waiting_owner(kanban, ledger):
    r = run(["pending", "--json"], kanban, ledger)
    assert r.returncode == 0, r.stderr
    rows = json.loads(r.stdout)
    assert [x["id"] for x in rows] == ["t-open", "t-finalize"]


def test_pending_json_shape_and_finalize_flag(kanban, ledger):
    rows = json.loads(run(["pending", "--json"], kanban, ledger).stdout)
    by_id = {x["id"]: x for x in rows}
    assert set(by_id["t-open"]) == {"id", "title", "question_text", "asked_at", "finalize",
                                    "goal", "priority"}
    assert by_id["t-open"]["finalize"] is False
    assert by_id["t-finalize"]["finalize"] is True
    assert by_id["t-open"]["asked_at"] == "2026-08-14 10:00"
    assert by_id["t-open"]["question_text"] == "May I refund 40 EUR?"


def test_pending_human_output_names_the_tasks(kanban, ledger):
    r = run(["pending"], kanban, ledger)
    assert r.returncode == 0
    assert "t-open" in r.stdout and "t-finalize" in r.stdout
    assert "t-todo" not in r.stdout and "t-answered" not in r.stdout


def test_pending_warns_when_policy_missing(kanban, ledger, tmp_path):
    env = dict(os.environ)
    env["APPROVER_LEDGER"] = str(ledger)
    env["APPROVER_POLICY"] = str(tmp_path / "nope.md")
    r = subprocess.run([sys.executable, APPROVE, "pending", "--tasks", str(kanban)],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0
    assert "WARNING" in r.stderr


# --- answer ------------------------------------------------------------------------------------

def test_answer_approve_writes_owner_fields_only(kanban, ledger):
    before = read_task(kanban, "t-open")
    r = run(["answer", "--id", "t-open", "--verdict", "approve",
             "--reason", "Under the 100 EUR ceiling.", "--policy-ref", "P3"], kanban, ledger)
    assert r.returncode == 0, r.stderr
    t = read_task(kanban, "t-open")
    assert t["question"]["answer"].startswith("APPROVED — ")
    assert "[policy: P3]" in t["question"]["answer"]
    assert t["question"]["answered_at"]
    assert t["question"]["text"] == before["question"]["text"]
    assert t["question"]["asked_at"] == before["question"]["asked_at"]
    assert t["status"] == "waiting_owner"           # the approver never moves the card
    assert len(t["journal"]) == len(before["journal"]) + 1
    assert "answered by approver agent (approve)" in t["journal"][-1]


def test_answer_reject_is_symmetric(kanban, ledger):
    r = run(["answer", "--id", "t-open", "--verdict", "reject",
             "--reason", "Production write is excluded."], kanban, ledger)
    assert r.returncode == 0, r.stderr
    t = read_task(kanban, "t-open")
    assert t["question"]["answer"].startswith("REJECTED — ")
    assert "[policy:" not in t["question"]["answer"]   # no refs given, none invented
    assert t["status"] == "waiting_owner"
    assert "answered by approver agent (reject)" in t["journal"][-1]


def test_answer_appends_ledger_entry(kanban, ledger):
    run(["answer", "--id", "t-open", "--verdict", "approve",
         "--reason", "Under the 100 EUR ceiling.", "--policy-ref", "P3,P4"], kanban, ledger)
    entries = ledger_lines(ledger)
    assert len(entries) == 1
    e = entries[0]
    assert e["task_id"] == "t-open"
    assert e["verdict"] == "approve"
    assert e["reason"] == "Under the 100 EUR ceiling."
    assert e["policy_clauses_cited"] == ["P3", "P4"]
    assert e["mode"] == "agent"
    assert e["question"] == "May I refund 40 EUR?"
    assert e["ts"]


def test_answer_leaves_other_tasks_untouched(kanban, ledger):
    before = json.loads(kanban.read_text(encoding="utf-8"))["tasks"]
    run(["answer", "--id", "t-open", "--verdict", "approve", "--reason", "ok"], kanban, ledger)
    after = json.loads(kanban.read_text(encoding="utf-8"))["tasks"]
    others = lambda ts: [t for t in ts if t["id"] != "t-open"]  # noqa: E731
    assert others(after) == others(before)


# --- guards ------------------------------------------------------------------------------------

@pytest.mark.parametrize("tid", ["t-todo", "t-answered", "t-unknown"])
def test_answer_refuses_non_answerable_tasks(kanban, ledger, tid):
    r = run(["answer", "--id", tid, "--verdict", "approve", "--reason", "nope"], kanban, ledger)
    assert r.returncode != 0
    assert r.stderr.strip()
    assert ledger_lines(ledger) == []               # a refused verdict is never logged


def test_answer_does_not_overwrite_an_existing_answer(kanban, ledger):
    run(["answer", "--id", "t-answered", "--verdict", "reject", "--reason", "no"], kanban, ledger)
    t = read_task(kanban, "t-answered")
    assert t["question"]["answer"] == "APPROVED — by the owner"
    assert t["question"]["answered_at"] == "2026-08-14 08:05"


def test_answer_refuses_an_empty_reason(kanban, ledger):
    r = run(["answer", "--id", "t-open", "--verdict", "approve", "--reason", "   "], kanban, ledger)
    assert r.returncode != 0
    assert read_task(kanban, "t-open")["question"]["answer"] is None


# --- escalate ----------------------------------------------------------------------------------

def test_escalate_leaves_the_task_identical(kanban, ledger):
    before = read_task(kanban, "t-finalize")
    r = run(["escalate", "--id", "t-finalize", "--reason", "Policy silent on production pushes."],
            kanban, ledger)
    assert r.returncode == 0, r.stderr
    assert read_task(kanban, "t-finalize") == before


def test_escalate_appends_an_escalated_ledger_entry(kanban, ledger):
    run(["escalate", "--id", "t-finalize", "--reason", "Policy silent on production pushes."],
        kanban, ledger)
    entries = ledger_lines(ledger)
    assert len(entries) == 1
    assert entries[0]["verdict"] == "escalated"
    assert entries[0]["task_id"] == "t-finalize"
    assert entries[0]["policy_clauses_cited"] == []
    assert entries[0]["mode"] == "agent"


def test_escalate_unknown_id_fails(kanban, ledger):
    r = run(["escalate", "--id", "t-nope", "--reason", "x"], kanban, ledger)
    assert r.returncode != 0
    assert ledger_lines(ledger) == []


# --- log ---------------------------------------------------------------------------------------

def test_log_returns_the_ledger_newest_last(kanban, ledger):
    run(["answer", "--id", "t-open", "--verdict", "approve", "--reason", "a"], kanban, ledger)
    run(["escalate", "--id", "t-finalize", "--reason", "b"], kanban, ledger)
    entries = json.loads(run(["log", "--json"], kanban, ledger).stdout)
    assert [e["verdict"] for e in entries] == ["approve", "escalated"]
    last = json.loads(run(["log", "--json", "--limit", "1"], kanban, ledger).stdout)
    assert [e["verdict"] for e in last] == ["escalated"]


# --- integration: the drop-in claim ------------------------------------------------------------

def test_taskrunner_consumes_the_approver_answer(kanban, ledger):
    """The real proof: the untouched taskrunner script accepts what the approver wrote."""
    assert os.path.isfile(UPDATE_TASK), "the taskrunner block must be present"
    r = run(["answer", "--id", "t-open", "--verdict", "approve",
             "--reason", "Under the 100 EUR ceiling.", "--policy-ref", "P3"], kanban, ledger)
    assert r.returncode == 0, r.stderr

    consumed = subprocess.run(
        [sys.executable, UPDATE_TASK, "--id", "t-open", "--consume-question",
         "--tasks", str(kanban)], capture_output=True, text=True)
    assert consumed.returncode == 0, consumed.stderr

    t = read_task(kanban, "t-open")
    assert t["question"] is None                       # the Q/A was archived and cleared
    assert any("Q/A consumed" in line for line in t["journal"])
    assert any("APPROVED" in line for line in t["journal"])
