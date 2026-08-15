#!/usr/bin/env python3
"""
Command Center dashboard — a minimal, read-only local view over the brain, the taskrunner kanban,
and the CRM. Python stdlib only: no build step, no dependencies, no external calls.

Run:    python3 server.py         then open http://localhost:8787
Config (env):
  DASH_PORT          default 8787
  DASH_BIND          interface to listen on. Default 127.0.0.1 (loopback)
  TASKRUNNER_TASKS   path to the taskrunner's tasks.json   (optional)
  CRM_DB             path to the crm block's crm.db          (optional)
  BRAIN_DIR          path to the brain root (reads main_brain.md)  (optional)
  APPROVER_LEDGER    path to the approver's decisions.jsonl (optional)
"""
import os, json, sqlite3, datetime, http.server, socketserver

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("DASH_PORT", "8787"))
# Default stays loopback, so laptop behaviour is unchanged. Set DASH_BIND=0.0.0.0 when the
# dashboard runs inside a VM behind a preview router, which cannot reach a loopback-only listener.
BIND = os.environ.get("DASH_BIND", "127.0.0.1")
TASKS = os.environ.get("TASKRUNNER_TASKS")
CRM_DB = os.environ.get("CRM_DB")
BRAIN_DIR = os.environ.get("BRAIN_DIR")
LEDGER = os.environ.get("APPROVER_LEDGER")
OPEN_STAGES = ["identified", "contacted", "met", "proposed", "negotiation", "won", "dormant"]
LEDGER_MAX = 200          # newest N are returned; the summary always counts every entry


def read_tasks():
    if not TASKS or not os.path.exists(TASKS):
        return {"available": False, "tasks": []}
    try:
        return {"available": True, "tasks": json.load(open(TASKS)).get("tasks", [])}
    except Exception:
        return {"available": False, "tasks": []}


def read_crm():
    if not CRM_DB or not os.path.exists(CRM_DB):
        return {"available": False}
    try:
        c = sqlite3.connect(CRM_DB)
        c.row_factory = sqlite3.Row
        companies = c.execute("SELECT COUNT(*) n FROM companies").fetchone()["n"]
        by_stage = {r["stage"]: r["n"] for r in
                    c.execute("SELECT stage, COUNT(*) n FROM projects GROUP BY stage")}
        today = datetime.date.today().isoformat()
        marks = ",".join("?" * len(OPEN_STAGES))
        due = c.execute(f"SELECT title, next_action, next_action_date FROM projects "
                        f"WHERE stage IN ({marks}) AND (next_action_date IS NULL OR next_action_date<=?) "
                        f"ORDER BY next_action_date", OPEN_STAGES + [today]).fetchall()
        c.close()
        return {"available": True, "companies": companies, "by_stage": by_stage,
                "due": [dict(r) for r in due]}
    except Exception as e:
        return {"available": False, "error": str(e)}


def read_brain():
    if not BRAIN_DIR:
        return {"available": False}
    f = os.path.join(BRAIN_DIR, "main_brain.md")
    if not os.path.exists(f):
        return {"available": False}
    txt = open(f, encoding="utf-8").read()
    return {"available": True, "text": txt[:4000]}


def read_decisions():
    """The approver's append-only audit trail (decisions.jsonl). Two kinds of entry share it:
    `mode: "agent"` — the policy decided, citing clauses; `mode: "human"` — the company bought a
    verified human's judgment and expensed it (`cost_usd`, `provider`). Read-only, like everything
    here: the dashboard never writes to the ledger it reports on."""
    if not LEDGER or not os.path.exists(LEDGER):
        return {"available": False, "decisions": []}
    entries, malformed = [], 0
    try:
        with open(LEDGER, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except ValueError:
                    malformed += 1      # one bad line must never blank the whole audit panel
    except OSError as e:
        return {"available": False, "error": str(e), "decisions": []}

    summary = {"total": len(entries), "by_verdict": {}, "by_mode": {},
               "human_cost_usd": 0.0, "malformed_lines": malformed}
    for e in entries:
        v = e.get("verdict") or "unknown"
        m = e.get("mode") or "unknown"
        summary["by_verdict"][v] = summary["by_verdict"].get(v, 0) + 1
        summary["by_mode"][m] = summary["by_mode"].get(m, 0) + 1
        if m == "human":
            try:
                summary["human_cost_usd"] += float(e.get("cost_usd") or 0)
            except (TypeError, ValueError):
                pass                    # a malformed cost must not hide the decision itself
    summary["human_cost_usd"] = round(summary["human_cost_usd"], 2)
    # Chronological order is preserved — reading top to bottom is the story of the day.
    return {"available": True, "summary": summary, "decisions": entries[-LEDGER_MAX:]}


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode("utf-8"))

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            try:
                self._send(200, open(os.path.join(HERE, "index.html"), "rb").read(), "text/html")
            except OSError:
                self._send(500, "index.html missing", "text/plain")
        elif self.path == "/api/tasks":
            self._send(200, json.dumps(read_tasks()))
        elif self.path == "/api/crm":
            self._send(200, json.dumps(read_crm()))
        elif self.path == "/api/brain":
            self._send(200, json.dumps(read_brain()))
        elif self.path == "/api/decisions":
            self._send(200, json.dumps(read_decisions()))
        else:
            self._send(404, "not found", "text/plain")

    def log_message(self, *args):
        pass  # quiet


def main():
    with socketserver.TCPServer((BIND, PORT), Handler) as httpd:
        print(f"Command Center dashboard on http://localhost:{PORT}  (Ctrl-C to stop)")
        print(f"  bind:  {BIND}")
        print(f"  tasks: {TASKS or '(unset TASKRUNNER_TASKS)'}")
        print(f"  crm:   {CRM_DB or '(unset CRM_DB)'}")
        print(f"  brain: {BRAIN_DIR or '(unset BRAIN_DIR)'}")
        print(f"  ledger:{LEDGER or '(unset APPROVER_LEDGER)'}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")


if __name__ == "__main__":
    main()
