#!/usr/bin/env python3
"""
Prospection — outbound sequences on top of the CRM (same SQLite database).

A sequence is 3-4 scheduled emails to one contact. Non-negotiable rule, embedded: **nothing is ever
sent without the owner's validation** — a sequence goes draft -> pending_validation -> approved, and
only approved steps whose date is due appear in `due-today`. The actual sending is done by the
`email-operator` block (or whatever email tool the founder uses); this block only manages the queue
and the validation gate.

Usage:  python3 prospection.py <command> [options]
Config: --db PATH or $CRM_DB (the SAME database as the crm block).
"""
import os, sys, sqlite3, argparse, datetime

SEQ_STATUS = ["draft", "pending_validation", "approved", "in_progress", "stopped", "done"]


def db_path(arg):
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("CRM_DB")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "crm.db")


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def today():
    return datetime.date.today().isoformat()


def connect(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS sequences (
      id INTEGER PRIMARY KEY, contact_id INTEGER, status TEXT NOT NULL DEFAULT 'draft',
      created_at TEXT);
    CREATE TABLE IF NOT EXISTS sequence_steps (
      id INTEGER PRIMARY KEY, sequence_id INTEGER REFERENCES sequences(id) ON DELETE CASCADE,
      step_no INTEGER, send_date TEXT, subject TEXT, body TEXT,
      status TEXT NOT NULL DEFAULT 'draft', sent_at TEXT);
    """)
    c.commit()
    return c


def cmd_create_sequence(c, a):
    # Guard: never sequence an opted-out contact (if the crm block's contacts table is present).
    try:
        row = c.execute("SELECT opted_out FROM contacts WHERE id=?", (a.contact,)).fetchone()
        if row and row["opted_out"]:
            sys.exit("ERROR: this contact is opted out — no sequence allowed.")
    except sqlite3.OperationalError:
        pass  # crm not initialized here; caller owns the contact id
    cur = c.execute("INSERT INTO sequences(contact_id,status,created_at) VALUES(?,?,?)",
                    (a.contact, "draft", now()))
    c.commit()
    print(f"OK sequence #{cur.lastrowid} (draft) for contact #{a.contact}")


def cmd_add_step(c, a):
    datetime.date.fromisoformat(a.date)
    seq = c.execute("SELECT * FROM sequences WHERE id=?", (a.sequence,)).fetchone()
    if not seq:
        sys.exit(f"ERROR: sequence #{a.sequence} not found.")
    n = c.execute("SELECT COALESCE(MAX(step_no),0)+1 n FROM sequence_steps WHERE sequence_id=?",
                  (a.sequence,)).fetchone()["n"]
    body = open(a.body_file, encoding="utf-8").read() if a.body_file else (a.body or "")
    cur = c.execute("INSERT INTO sequence_steps(sequence_id,step_no,send_date,subject,body,status) "
                    "VALUES(?,?,?,?,?,?)", (a.sequence, n, a.date, a.subject, body, "draft"))
    c.commit()
    print(f"OK step #{cur.lastrowid} (#{n}) on {a.date} — {a.subject}")


def cmd_submit(c, a):
    seq = c.execute("SELECT * FROM sequences WHERE id=?", (a.sequence,)).fetchone()
    if not seq:
        sys.exit(f"ERROR: sequence #{a.sequence} not found.")
    if not c.execute("SELECT 1 FROM sequence_steps WHERE sequence_id=?", (a.sequence,)).fetchone():
        sys.exit("ERROR: sequence has no steps.")
    c.execute("UPDATE sequences SET status='pending_validation' WHERE id=?", (a.sequence,))
    c.commit()
    print(f"OK sequence #{a.sequence} -> pending_validation (waiting for the owner to approve)")


def cmd_approve(c, a):
    """Owner action: approve the whole sequence (all its steps)."""
    seq = c.execute("SELECT * FROM sequences WHERE id=?", (a.sequence,)).fetchone()
    if not seq:
        sys.exit(f"ERROR: sequence #{a.sequence} not found.")
    c.execute("UPDATE sequences SET status='approved' WHERE id=?", (a.sequence,))
    c.execute("UPDATE sequence_steps SET status='approved' WHERE sequence_id=? AND status='draft'",
              (a.sequence,))
    c.commit()
    print(f"OK sequence #{a.sequence} approved — its due steps will appear in `due-today`")


def cmd_due_today(c, a):
    d = a.date or today()
    rows = c.execute(
        "SELECT st.*, s.contact_id FROM sequence_steps st JOIN sequences s ON s.id=st.sequence_id "
        "WHERE st.status='approved' AND st.send_date<=? AND st.sent_at IS NULL "
        "AND s.status IN ('approved','in_progress') ORDER BY st.send_date", (d,)).fetchall()
    if not rows:
        print("Nothing due — no approved step to send.")
        return
    for r in rows:
        print(f"  step #{r['id']} (seq #{r['sequence_id']}, contact #{r['contact_id']}) "
              f"due {r['send_date']} — {r['subject']}")


def cmd_mark_sent(c, a):
    st = c.execute("SELECT * FROM sequence_steps WHERE id=?", (a.step,)).fetchone()
    if not st:
        sys.exit(f"ERROR: step #{a.step} not found.")
    if st["status"] != "approved":
        sys.exit(f"ERROR: step #{a.step} is '{st['status']}', not approved — can't mark sent.")
    c.execute("UPDATE sequence_steps SET status='sent', sent_at=? WHERE id=?", (now(), a.step))
    c.execute("UPDATE sequences SET status='in_progress' WHERE id=?", (st["sequence_id"],))
    c.commit()
    print(f"OK step #{a.step} marked sent")


def cmd_reply_received(c, a):
    """A reply came in: stop every active sequence to that contact."""
    n = c.execute("UPDATE sequences SET status='stopped' WHERE contact_id=? "
                  "AND status IN ('approved','in_progress','pending_validation')", (a.contact,)).rowcount
    c.commit()
    print(f"OK stopped {n} sequence(s) for contact #{a.contact} (reply received)")


def cmd_show(c, a):
    seq = c.execute("SELECT * FROM sequences WHERE id=?", (a.sequence,)).fetchone()
    if not seq:
        sys.exit(f"ERROR: sequence #{a.sequence} not found.")
    print(f"# sequence #{seq['id']} — contact #{seq['contact_id']} — {seq['status']}")
    for st in c.execute("SELECT * FROM sequence_steps WHERE sequence_id=? ORDER BY step_no", (a.sequence,)):
        mark = "sent" if st["status"] == "sent" else st["status"]
        print(f"  {st['step_no']}. [{mark}] {st['send_date']} — {st['subject']}")


def build_parser():
    ap = argparse.ArgumentParser(description="Outbound sequences on the CRM database")
    ap.add_argument("--db")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("create-sequence"); s.add_argument("--contact", type=int, required=True)
    s.set_defaults(f=cmd_create_sequence)
    s = sub.add_parser("add-step"); s.add_argument("--sequence", type=int, required=True)
    s.add_argument("--date", required=True); s.add_argument("--subject", required=True)
    s.add_argument("--body"); s.add_argument("--body-file"); s.set_defaults(f=cmd_add_step)
    s = sub.add_parser("submit"); s.add_argument("--sequence", type=int, required=True); s.set_defaults(f=cmd_submit)
    s = sub.add_parser("approve", help="owner: approve a pending sequence"); s.add_argument("--sequence", type=int, required=True)
    s.set_defaults(f=cmd_approve)
    s = sub.add_parser("due-today"); s.add_argument("--date"); s.set_defaults(f=cmd_due_today)
    s = sub.add_parser("mark-sent"); s.add_argument("--step", type=int, required=True); s.set_defaults(f=cmd_mark_sent)
    s = sub.add_parser("reply-received"); s.add_argument("--contact", type=int, required=True); s.set_defaults(f=cmd_reply_received)
    s = sub.add_parser("show"); s.add_argument("--sequence", type=int, required=True); s.set_defaults(f=cmd_show)
    return ap


def main():
    a = build_parser().parse_args()
    c = connect(db_path(a.db))
    try:
        a.f(c, a)
    finally:
        c.close()


if __name__ == "__main__":
    main()
