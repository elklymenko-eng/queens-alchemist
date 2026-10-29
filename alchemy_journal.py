"""Opt-in, user-owned Alchemy Journal. No AI-inferred facts are saved."""
import sqlite3

FIELDS = {
    "vision": "Dream relationship & how I want to feel",
    "standards": "Values, standards & green flags",
    "patterns": "Patterns I have recognized",
    "inner_union": "Inner union & archetypal insights",
    "practices": "Embodiment practices that help",
    "next_step": "My next loving step",
}
MAX_ENTRY = 1200

def initialize(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS journal_preferences (user_id INTEGER PRIMARY KEY, offered INTEGER NOT NULL DEFAULT 0, declined INTEGER NOT NULL DEFAULT 0, last_offer_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS journal_proposals (user_id INTEGER PRIMARY KEY, field TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS alchemy_journal (
        user_id INTEGER NOT NULL,
        field TEXT NOT NULL,
        content TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, field)
    )""")

def get_entries(conn, uid):
    return dict(conn.execute(
        "SELECT field, content FROM alchemy_journal WHERE user_id=? ORDER BY field",
        (uid,)).fetchall())

def set_entry(conn, uid, field, content):
    if field not in FIELDS:
        raise ValueError("Unknown journal field")
    content = content.strip()
    if not content or len(content) > MAX_ENTRY:
        raise ValueError("Entry must be 1 to 1200 characters")
    conn.execute("""INSERT INTO alchemy_journal (user_id, field, content)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, field) DO UPDATE SET
        content=excluded.content, updated_at=CURRENT_TIMESTAMP""",
        (uid, field, content))

def clear(conn, uid):
    conn.execute("DELETE FROM alchemy_journal WHERE user_id=?", (uid,))

def render(entries):
    if not entries:
        return "👑 Your Alchemy Journal is blank. Nothing is saved automatically.\n\nTo begin, send /remember vision followed by what you want to create.\n\nOther sections: " + ", ".join(FIELDS)
    parts = ["👑 Your Alchemy Journal — written by you:"]
    for field, label in FIELDS.items():
        if field in entries:
            parts.append("\n" + label + ":\n" + entries[field])
    parts.append("\nEdit: /remember vision Your updated vision\nErase everything: /clearjournal")
    return "\n".join(parts)

def propose(conn, uid, field, content):
    if field not in FIELDS or not content.strip() or len(content) > MAX_ENTRY:
        return False
    conn.execute("""INSERT INTO journal_proposals(user_id,field,content)
        VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET
        field=excluded.field,content=excluded.content,created_at=CURRENT_TIMESTAMP""",
        (uid, field, content.strip()))
    conn.execute("""INSERT INTO journal_preferences(user_id,offered,last_offer_at)
        VALUES(?,1,CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
        offered=1,last_offer_at=CURRENT_TIMESTAMP""", (uid,))
    return True

def pending(conn, uid):
    return conn.execute("SELECT field,content FROM journal_proposals WHERE user_id=?", (uid,)).fetchone()

def dismiss(conn, uid):
    conn.execute("DELETE FROM journal_proposals WHERE user_id=?", (uid,))

def decline(conn, uid):
    dismiss(conn, uid)
    conn.execute("""INSERT INTO journal_preferences(user_id,offered,declined)
        VALUES(?,1,1) ON CONFLICT(user_id) DO UPDATE SET declined=1""", (uid,))

def can_offer(conn, uid):
    row = conn.execute("""SELECT offered,declined,last_offer_at
        FROM journal_preferences WHERE user_id=?""", (uid,)).fetchone()
    if pending(conn, uid) or (row and row[1]):
        return False
    if row and row[2]:
        recent = conn.execute("""SELECT datetime(?) > datetime('now','-7 days')""",
                              (row[2],)).fetchone()[0]
        if recent:
            return False
    return True
