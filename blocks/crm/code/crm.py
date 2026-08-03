#!/usr/bin/env python3
"""
CRM — a local-first, single-file CRM for the Command Center. Generalized from a working system,
rebuilt on SQLite so it needs no external account and no secret.

Model: companies -> contacts, and projects (any origin) with a **dated next action**. Every
interaction is logged; every significant mutation writes an event (the learning journal).

Non-negotiable rules, embedded (agents can't route around them):
- An OPEN project must always carry a next action + a next-action date ("nothing sleeps"). Closing a
  project (won-and-delivered or lost) is the only way to drop the next action.
- Disqualifying a company requires --reason.
- Every mutation logs an event.

Usage:  python3 crm.py <command> [options]      (--help on each)
Config: --db PATH  or  $CRM_DB  (default: crm.db next to this script)
"""
import os, sys, json, sqlite3, argparse, datetime

COMPANY_STATUS = ["new", "qualifying", "disqualified", "qualified", "in_touch", "client"]
STAGES = ["identified", "contacted", "met", "proposed", "negotiation", "won", "delivered",
          "lost", "dormant"]
OPEN_STAGES = ["identified", "contacted", "met", "proposed", "negotiation", "won", "dormant"]
TERMINAL_STAGES = ["delivered", "lost"]
CHANNELS = ["email", "call", "meeting", "linkedin", "whatsapp", "event", "other"]


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
    CREATE TABLE IF NOT EXISTS companies (
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new',
      source TEXT, website TEXT, notes TEXT, created_at TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS contacts (
      id INTEGER PRIMARY KEY, company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
      name TEXT NOT NULL, role TEXT, email TEXT, phone TEXT, opted_out INTEGER DEFAULT 0,
      created_at TEXT);
    CREATE TABLE IF NOT EXISTS projects (
      id INTEGER PRIMARY KEY, company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
      title TEXT NOT NULL, stage TEXT NOT NULL DEFAULT 'identified', amount REAL,
      next_action TEXT, next_action_date TEXT, created_at TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS interactions (
      id INTEGER PRIMARY KEY, company_id INTEGER, contact_id INTEGER, project_id INTEGER,
      channel TEXT, summary TEXT, at TEXT);
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY, type TEXT NOT NULL, company_id INTEGER, contact_id INTEGER,
      project_id INTEGER, reason TEXT, at TEXT);
    """)
    c.commit()
    return c


def log_event(c, type_, company_id=None, contact_id=None, project_id=None, reason=None):
    c.execute("INSERT INTO events(type,company_id,contact_id,project_id,reason,at) VALUES(?,?,?,?,?,?)",
              (type_, company_id, contact_id, project_id, reason, now()))


# ── commands ──────────────────────────────────────────────────────────────────
def cmd_init(c, a):
    print(f"OK CRM ready at {a._db}")


def cmd_add_company(c, a):
    cur = c.execute("INSERT INTO companies(name,status,source,website,notes,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (a.name, a.status, a.source, a.website, a.notes, now(), now()))
    cid = cur.lastrowid
    log_event(c, "company_added", company_id=cid)
    c.commit()
    print(f"OK company #{cid} — {a.name} ({a.status})")


def cmd_set_status(c, a):
    if a.status == "disqualified" and not (a.reason or "").strip():
        sys.exit("ERROR: disqualifying requires --reason.")
    row = c.execute("SELECT id FROM companies WHERE id=?", (a.id,)).fetchone()
    if not row:
        sys.exit(f"ERROR: company #{a.id} not found.")
    c.execute("UPDATE companies SET status=?, updated_at=? WHERE id=?", (a.status, now(), a.id))
    log_event(c, "status_changed", company_id=a.id, reason=a.reason)
    c.commit()
    print(f"OK company #{a.id} -> {a.status}")


def cmd_add_contact(c, a):
    row = c.execute("SELECT id FROM companies WHERE id=?", (a.company,)).fetchone()
    if not row:
        sys.exit(f"ERROR: company #{a.company} not found.")
    cur = c.execute("INSERT INTO contacts(company_id,name,role,email,phone,created_at) "
                    "VALUES(?,?,?,?,?,?)", (a.company, a.name, a.role, a.email, a.phone, now()))
    log_event(c, "contact_added", company_id=a.company, contact_id=cur.lastrowid)
    c.commit()
    print(f"OK contact #{cur.lastrowid} — {a.name} @ company #{a.company}")


def _require_next(a):
    if a.stage not in TERMINAL_STAGES:
        if not (a.next or "").strip() or not (a.next_date or "").strip():
            sys.exit("ERROR: an open project needs --next and --next-date (nothing sleeps). "
                     "Only 'delivered'/'lost' may omit them.")
        datetime.date.fromisoformat(a.next_date)  # validate


def cmd_project_add(c, a):
    _require_next(a)
    cur = c.execute("INSERT INTO projects(company_id,title,stage,amount,next_action,"
                    "next_action_date,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                    (a.company, a.title, a.stage, a.amount,
                     (a.next or None), (a.next_date or None), now(), now()))
    log_event(c, "project_added", company_id=a.company, project_id=cur.lastrowid)
    c.commit()
    print(f"OK project #{cur.lastrowid} — {a.title} [{a.stage}]")


def cmd_project_move(c, a):
    row = c.execute("SELECT * FROM projects WHERE id=?", (a.id,)).fetchone()
    if not row:
        sys.exit(f"ERROR: project #{a.id} not found.")
    if a.stage not in TERMINAL_STAGES and not ((a.next or "").strip() and (a.next_date or "").strip()):
        sys.exit("ERROR: moving to an open stage needs --next and --next-date (nothing sleeps).")
    if a.next_date:
        datetime.date.fromisoformat(a.next_date)
    nxt = (a.next or None) if a.stage not in TERMINAL_STAGES else None
    nxt_d = (a.next_date or None) if a.stage not in TERMINAL_STAGES else None
    c.execute("UPDATE projects SET stage=?, next_action=?, next_action_date=?, updated_at=? WHERE id=?",
              (a.stage, nxt, nxt_d, now(), a.id))
    log_event(c, "project_moved", project_id=a.id, reason=a.stage)
    c.commit()
    print(f"OK project #{a.id} -> {a.stage}")


def cmd_project_touch(c, a):
    row = c.execute("SELECT * FROM projects WHERE id=?", (a.id,)).fetchone()
    if not row:
        sys.exit(f"ERROR: project #{a.id} not found.")
    datetime.date.fromisoformat(a.next_date)
    c.execute("INSERT INTO interactions(company_id,project_id,channel,summary,at) VALUES(?,?,?,?,?)",
              (row["company_id"], a.id, a.channel, a.summary, now()))
    c.execute("UPDATE projects SET next_action=?, next_action_date=?, updated_at=? WHERE id=?",
              (a.next, a.next_date, now(), a.id))
    log_event(c, "project_touched", project_id=a.id)
    c.commit()
    print(f"OK project #{a.id} touched — next: {a.next} ({a.next_date})")


def cmd_note(c, a):
    c.execute("INSERT INTO interactions(company_id,contact_id,channel,summary,at) VALUES(?,?,?,?,?)",
              (a.company, a.contact, a.channel, a.summary, now()))
    log_event(c, "note_added", company_id=a.company, contact_id=a.contact)
    c.commit()
    print("OK note logged")


def cmd_list(c, a):
    q = "SELECT id,name,status,source FROM companies"
    p = []
    if a.status:
        q += " WHERE status=?"; p.append(a.status)
    q += " ORDER BY id"
    for r in c.execute(q, p):
        print(f"  #{r['id']:>3}  {r['name']}  [{r['status']}]" + (f"  ({r['source']})" if r['source'] else ""))


def cmd_show(c, a):
    co = c.execute("SELECT * FROM companies WHERE id=?", (a.id,)).fetchone()
    if not co:
        sys.exit(f"ERROR: company #{a.id} not found.")
    print(f"# {co['name']}  (#{co['id']}, {co['status']})")
    if co["website"]:
        print(f"  web: {co['website']}")
    print("  contacts:")
    for ct in c.execute("SELECT * FROM contacts WHERE company_id=?", (a.id,)):
        print(f"    - {ct['name']} — {ct['role'] or ''}  {ct['email'] or ''}  {ct['phone'] or ''}")
    print("  projects:")
    for pr in c.execute("SELECT * FROM projects WHERE company_id=?", (a.id,)):
        na = f" — next: {pr['next_action']} ({pr['next_action_date']})" if pr["next_action"] else ""
        print(f"    - #{pr['id']} {pr['title']} [{pr['stage']}]{na}")


def cmd_relances(c, a):
    """Open projects whose next action is due today or overdue, or that (bug) have none."""
    rows = c.execute("SELECT p.*, co.name AS company FROM projects p "
                     "LEFT JOIN companies co ON co.id=p.company_id "
                     f"WHERE p.stage IN ({','.join('?'*len(OPEN_STAGES))}) ORDER BY p.next_action_date",
                     OPEN_STAGES).fetchall()
    due = [r for r in rows if not r["next_action_date"] or r["next_action_date"] <= today()]
    if not due:
        print("Nothing due — every open project has a future next action.")
        return
    for r in due:
        tag = "NO NEXT ACTION" if not r["next_action_date"] else f"due {r['next_action_date']}"
        print(f"  #{r['id']} {r['title']} [{r['stage']}] @ {r['company'] or '?'}  [{tag}]  "
              f"{r['next_action'] or ''}")


def cmd_stats(c, a):
    print("companies by status:")
    for r in c.execute("SELECT status, COUNT(*) n FROM companies GROUP BY status"):
        print(f"  {r['status']:>13}: {r['n']}")
    print("projects by stage:")
    for r in c.execute("SELECT stage, COUNT(*) n FROM projects GROUP BY stage"):
        print(f"  {r['stage']:>13}: {r['n']}")
    signed = c.execute("SELECT COALESCE(SUM(amount),0) s FROM projects WHERE stage IN ('won','delivered')").fetchone()["s"]
    inplay = c.execute("SELECT COALESCE(SUM(amount),0) s FROM projects WHERE stage IN "
                       "('identified','contacted','met','proposed','negotiation')").fetchone()["s"]
    print(f"amount — signed: {signed:.0f} · in play: {inplay:.0f}  (never sum the two)")


def build_parser():
    ap = argparse.ArgumentParser(description="Local-first CRM")
    ap.add_argument("--db", help="database file (default: $CRM_DB or crm.db next to this script)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init").set_defaults(f=cmd_init)

    s = sub.add_parser("add-company"); s.add_argument("--name", required=True)
    s.add_argument("--status", default="new", choices=COMPANY_STATUS)
    s.add_argument("--source"); s.add_argument("--website"); s.add_argument("--notes")
    s.set_defaults(f=cmd_add_company)

    s = sub.add_parser("set-status"); s.add_argument("--id", type=int, required=True)
    s.add_argument("--status", required=True, choices=COMPANY_STATUS); s.add_argument("--reason")
    s.set_defaults(f=cmd_set_status)

    s = sub.add_parser("add-contact"); s.add_argument("--company", type=int, required=True)
    s.add_argument("--name", required=True); s.add_argument("--role")
    s.add_argument("--email"); s.add_argument("--phone"); s.set_defaults(f=cmd_add_contact)

    s = sub.add_parser("project-add"); s.add_argument("--company", type=int)
    s.add_argument("--title", required=True); s.add_argument("--stage", default="identified", choices=STAGES)
    s.add_argument("--amount", type=float); s.add_argument("--next"); s.add_argument("--next-date")
    s.set_defaults(f=cmd_project_add)

    s = sub.add_parser("project-move"); s.add_argument("--id", type=int, required=True)
    s.add_argument("--stage", required=True, choices=STAGES)
    s.add_argument("--next"); s.add_argument("--next-date"); s.set_defaults(f=cmd_project_move)

    s = sub.add_parser("project-touch"); s.add_argument("--id", type=int, required=True)
    s.add_argument("--channel", default="other", choices=CHANNELS); s.add_argument("--summary", required=True)
    s.add_argument("--next", required=True); s.add_argument("--next-date", required=True)
    s.set_defaults(f=cmd_project_touch)

    s = sub.add_parser("note"); s.add_argument("--company", type=int); s.add_argument("--contact", type=int)
    s.add_argument("--channel", default="other", choices=CHANNELS); s.add_argument("--summary", required=True)
    s.set_defaults(f=cmd_note)

    s = sub.add_parser("list"); s.add_argument("--status", choices=COMPANY_STATUS); s.set_defaults(f=cmd_list)
    s = sub.add_parser("show"); s.add_argument("--id", type=int, required=True); s.set_defaults(f=cmd_show)
    sub.add_parser("relances", help="open projects due/overdue or missing a next action").set_defaults(f=cmd_relances)
    sub.add_parser("stats").set_defaults(f=cmd_stats)
    return ap


def main():
    a = build_parser().parse_args()
    a._db = db_path(a.db)
    c = connect(a._db)
    try:
        a.f(c, a)
    finally:
        c.close()


if __name__ == "__main__":
    main()
