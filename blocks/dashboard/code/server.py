#!/usr/bin/env python3
"""
Command Center dashboard — a minimal, read-only local view over the brain, the taskrunner kanban,
and the CRM. Python stdlib only: no build step, no dependencies, no external calls.

Run:    python3 server.py         then open http://localhost:8787
Config (env):
  DASH_PORT          default 8787
  TASKRUNNER_TASKS   path to the taskrunner's tasks.json   (optional)
  CRM_DB             path to the crm block's crm.db          (optional)
  BRAIN_DIR          path to the brain root (reads main_brain.md)  (optional)
"""
import os, json, sqlite3, datetime, http.server, socketserver

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("DASH_PORT", "8787"))
TASKS = os.environ.get("TASKRUNNER_TASKS")
CRM_DB = os.environ.get("CRM_DB")
BRAIN_DIR = os.environ.get("BRAIN_DIR")
OPEN_STAGES = ["identified", "contacted", "met", "proposed", "negotiation", "won", "dormant"]


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
        else:
            self._send(404, "not found", "text/plain")

    def log_message(self, *args):
        pass  # quiet


def main():
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Command Center dashboard on http://localhost:{PORT}  (Ctrl-C to stop)")
        print(f"  tasks: {TASKS or '(unset TASKRUNNER_TASKS)'}")
        print(f"  crm:   {CRM_DB or '(unset CRM_DB)'}")
        print(f"  brain: {BRAIN_DIR or '(unset BRAIN_DIR)'}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")


if __name__ == "__main__":
    main()
