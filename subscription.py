"""Telegram Stars subscription and monthly AI usage accounting."""
import sqlite3
from datetime import datetime, timezone

PRICE_STARS = 199
PERIOD_SECONDS = 2592000
MONTHLY_REPLY_CAP = 300
PAYLOAD = "queens_alchemist_monthly_v1"

def initialize(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS paid_subscriptions (
        user_id INTEGER PRIMARY KEY,
        expires_at INTEGER NOT NULL,
        charge_id TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS paid_usage (
        user_id INTEGER NOT NULL, cycle_start INTEGER NOT NULL,
        replies INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (user_id, cycle_start)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS processed_charges (
        charge_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL
    )""")

def now():
    return int(datetime.now(timezone.utc).timestamp())

def active(conn, uid, timestamp=None):
    timestamp = now() if timestamp is None else timestamp
    row = conn.execute("SELECT expires_at FROM paid_subscriptions WHERE user_id=?", (uid,)).fetchone()
    return bool(row and row[0] > timestamp)

def cycle(conn, uid, timestamp=None):
    timestamp = now() if timestamp is None else timestamp
    row = conn.execute("SELECT expires_at FROM paid_subscriptions WHERE user_id=?", (uid,)).fetchone()
    if not row or row[0] <= timestamp:
        return None
    # Fixed 30-day windows counted back from the current subscription expiration.
    return row[0] - PERIOD_SECONDS

def remaining(conn, uid, timestamp=None):
    start = cycle(conn, uid, timestamp)
    if start is None:
        return 0
    row = conn.execute("SELECT replies FROM paid_usage WHERE user_id=? AND cycle_start=?", (uid, start)).fetchone()
    return max(0, MONTHLY_REPLY_CAP - (row[0] if row else 0))

def record_reply(conn, uid):
    start = cycle(conn, uid)
    if start is None:
        return
    conn.execute("""INSERT INTO paid_usage (user_id, cycle_start, replies)
                    VALUES (?, ?, 1) ON CONFLICT(user_id,cycle_start)
                    DO UPDATE SET replies=replies+1""", (uid, start))

def record_payment(conn, uid, charge_id, expires_at):
    if not charge_id or expires_at <= now():
        return False
    cur = conn.execute("INSERT OR IGNORE INTO processed_charges(charge_id,user_id) VALUES (?,?)", (charge_id, uid))
    if cur.rowcount == 0:
        return False
    conn.execute("""INSERT INTO paid_subscriptions(user_id,expires_at,charge_id)
                    VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET
                    expires_at=max(expires_at,excluded.expires_at),
                    charge_id=CASE WHEN excluded.expires_at>=expires_at THEN excluded.charge_id ELSE charge_id END,
                    updated_at=CURRENT_TIMESTAMP""", (uid, expires_at, charge_id))
    return True
