"""
Deterministic tests for US-1.2 glue (`record_sales.py`). No network, no Stripe key.

`pay.py sales` is substituted with the hidden `--from-file PATH` test/ops hook (documented in
record_sales.py's module docstring) — a JSON file in the exact shape `pay.py sales --json` prints.
Every CRM write goes through a REAL temporary sqlite database via the real `crm.py` CLI (subprocess
init, then `add-company` / `project-add`), and every assertion about what landed in the CRM is made
by parsing `crm.py`'s OWN `stats` / `show` command output — never by reading the sqlite file
directly — so these tests prove the two CLIs actually agree with each other, not just that this
tool believes they do.
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
RECORD_SALES_PY = os.path.join(os.path.dirname(HERE), "code", "record_sales.py")
CRM_PY = os.path.abspath(os.path.join(os.path.dirname(HERE), "..", "crm", "code", "crm.py"))

TIMEOUT = 30


# ── helpers ───────────────────────────────────────────────────────────────────
def run_record_sales(*args):
    proc = subprocess.run([sys.executable, RECORD_SALES_PY, *args],
                           capture_output=True, text=True, timeout=TIMEOUT)
    return proc


def run_crm(crm_db, *args):
    proc = subprocess.run([sys.executable, CRM_PY, "--db", str(crm_db), *args],
                           capture_output=True, text=True, timeout=TIMEOUT)
    return proc


def write_sales(path, sales):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sales, f)


def sale(session_id, amount_usd=19.0, title="Sunday Playbook", link_id="plink_test", currency="usd"):
    return {
        "link_id": link_id,
        "session_id": session_id,
        "title": title,
        "amount_usd": amount_usd,
        "currency": currency,
        "paid_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.fixture
def env(tmp_path):
    """Everything a run needs, isolated per test: a fresh sales fixture file, a fresh crm.db (not
    yet created — proves the auto-init path), and a fresh state file."""
    return {
        "sales_file": tmp_path / "sales.json",
        "crm_db": tmp_path / "crm.db",
        "state": tmp_path / "recorded.jsonl",
    }


# ── recording ─────────────────────────────────────────────────────────────────
def test_run_records_new_paid_sales_into_crm(env):
    write_sales(env["sales_file"], [
        sale("cs_test_AAAAAAAA1111", amount_usd=19.0),
        sale("cs_test_BBBBBBBB2222", amount_usd=29.5, title="Sunday Deep Dive"),
    ])

    proc = run_record_sales("run", "--json", "--from-file", str(env["sales_file"]),
                             "--crm-db", str(env["crm_db"]), "--state", str(env["state"]))
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert len(out["recorded"]) == 2
    assert out["already_recorded"] == []
    assert out["failed"] == []
    assert all(e["crm_project_id"] is not None for e in out["recorded"])

    # crm.db was created automatically (auto-init path, no pre-existing database).
    assert env["crm_db"].exists()

    # State file has exactly the two entries, both marked recorded.
    lines = env["state"].read_text().splitlines()
    assert len(lines) == 2
    for line in lines:
        entry = json.loads(line)
        assert entry["status"] == "recorded"
        assert entry["crm_project_id"] is not None

    # Verify via crm.py's OWN stats command: two 'won' projects, signed amount = 19.0 + 29.5.
    stats = run_crm(env["crm_db"], "stats")
    assert stats.returncode == 0, stats.stderr
    assert "won: 2" in stats.stdout
    assert "signed: 48" in stats.stdout or "signed: 49" in stats.stdout  # 48.5 rounds via :.0f

    # Verify via crm.py's OWN show command: the company + both projects, stage [won].
    list_out = run_crm(env["crm_db"], "list")
    assert list_out.returncode == 0
    assert "Direct sales" in list_out.stdout
    company_id = list_out.stdout.strip().splitlines()[0].split("#")[1].split()[0]
    show = run_crm(env["crm_db"], "show", "--id", company_id)
    assert show.returncode == 0, show.stderr
    assert "[won]" in show.stdout
    assert show.stdout.count("[won]") == 2
    assert "1111" in show.stdout and "2222" in show.stdout  # short session-id suffix in the title


def test_run_is_idempotent(env):
    write_sales(env["sales_file"], [sale("cs_test_IDEMPOTENT01", amount_usd=10.0)])

    first = run_record_sales("run", "--json", "--from-file", str(env["sales_file"]),
                              "--crm-db", str(env["crm_db"]), "--state", str(env["state"]))
    assert first.returncode == 0, first.stderr
    assert len(json.loads(first.stdout)["recorded"]) == 1

    second = run_record_sales("run", "--json", "--from-file", str(env["sales_file"]),
                               "--crm-db", str(env["crm_db"]), "--state", str(env["state"]))
    assert second.returncode == 0, second.stderr
    out = json.loads(second.stdout)
    assert out["recorded"] == []                        # nothing new recorded
    assert out["already_recorded"] == ["cs_test_IDEMPOTENT01"]

    # Only ONE project exists in the CRM — no duplicate from the second run.
    stats = run_crm(env["crm_db"], "stats")
    assert "won: 1" in stats.stdout

    # State file still has exactly one line.
    assert len(env["state"].read_text().splitlines()) == 1


def test_partial_failure_records_others_and_retries_the_bad_one(env):
    write_sales(env["sales_file"], [
        sale("cs_test_GOOD00001", amount_usd=15.0),
        sale("cs_test_BAD000002", amount_usd="not-a-number"),  # crm.py's --amount type=float rejects this
    ])

    first = run_record_sales("run", "--json", "--from-file", str(env["sales_file"]),
                              "--crm-db", str(env["crm_db"]), "--state", str(env["state"]))
    assert first.returncode == 1                       # any failure -> exit 1
    out = json.loads(first.stdout)
    assert [e["session_id"] for e in out["recorded"]] == ["cs_test_GOOD00001"]
    assert [f["session_id"] for f in out["failed"]] == ["cs_test_BAD000002"]

    # Only the good sale is durably recorded.
    lines = [json.loads(l) for l in env["state"].read_text().splitlines()]
    assert len(lines) == 1
    assert lines[0]["session_id"] == "cs_test_GOOD00001"

    stats = run_crm(env["crm_db"], "stats")
    assert "won: 1" in stats.stdout

    # Run again with the SAME (still-bad) fixture: the good sale is skipped, the bad one is
    # retried (not silently dropped) and fails again — proving retry-on-next-run, not a permanent skip.
    second = run_record_sales("run", "--json", "--from-file", str(env["sales_file"]),
                               "--crm-db", str(env["crm_db"]), "--state", str(env["state"]))
    assert second.returncode == 1
    out2 = json.loads(second.stdout)
    assert out2["recorded"] == []
    assert out2["already_recorded"] == ["cs_test_GOOD00001"]
    assert [f["session_id"] for f in out2["failed"]] == ["cs_test_BAD000002"]

    # Still only one project in the CRM — the bad one never landed, on either run.
    stats2 = run_crm(env["crm_db"], "stats")
    assert "won: 1" in stats2.stdout
    assert len(env["state"].read_text().splitlines()) == 1


def test_log_dumps_the_state_file(env):
    write_sales(env["sales_file"], [sale("cs_test_LOGCHECK01", amount_usd=42.0)])
    run_record_sales("run", "--from-file", str(env["sales_file"]),
                      "--crm-db", str(env["crm_db"]), "--state", str(env["state"]))

    proc = run_record_sales("log", "--json", "--state", str(env["state"]))
    assert proc.returncode == 0, proc.stderr
    entries = json.loads(proc.stdout)
    assert len(entries) == 1
    assert entries[0]["session_id"] == "cs_test_LOGCHECK01"
    assert entries[0]["amount_usd"] == 42.0

    proc_empty = run_record_sales("log", "--json",
                                   "--state", str(env["state"].parent / "never-created.jsonl"))
    assert proc_empty.returncode == 0
    assert json.loads(proc_empty.stdout) == []


def test_no_new_sales_exits_zero(env):
    write_sales(env["sales_file"], [])
    proc = run_record_sales("run", "--json", "--from-file", str(env["sales_file"]),
                             "--crm-db", str(env["crm_db"]), "--state", str(env["state"]))
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out == {"recorded": [], "already_recorded": [], "failed": []}


def test_from_file_missing_is_a_clean_error(env):
    proc = run_record_sales("run", "--from-file", str(env["sales_file"]),  # never written
                             "--crm-db", str(env["crm_db"]), "--state", str(env["state"]))
    assert proc.returncode == 1
    assert "ERROR" in proc.stderr
