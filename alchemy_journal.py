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
