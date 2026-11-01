"""Opt-in daily transmissions. One delivery per local calendar day."""
import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

log = logging.getLogger("daily_alchemy")
ZONES = [
    ("Toronto / New York", "America/Toronto"),
    ("Vancouver / Los Angeles", "America/Vancouver"),
    ("Calgary / Denver", "America/Edmonton"),
    ("Winnipeg / Chicago", "America/Winnipeg"),
    ("Halifax", "America/Halifax"),
    ("London", "Europe/London"),
    ("Central Europe", "Europe/Paris"),
    ("Kyiv", "Europe/Kyiv"),
    ("Sydney", "Australia/Sydney"),
    ("UTC / Other", "UTC"),
]
MESSAGES = [
    ("The Art of Receiving", "You don't have to earn every kindness. Sometimes the most magnetic move is simply allowing yourself to receive.", "Accept one compliment or gesture of care with a warm thank-you."),
    ("The Queen's Discernment", "Chemistry is delicious. Consistency is what makes love feel safe.", "Notice who follows through on a small promise today."),
    ("Your Inner Protector", "Your heart may remain open while your standards remain beautifully intact.", "Name one loving boundary that protects the relationship you want to create."),
    ("The Lover's Joy", "Your pleasure isn't a reward for getting everything done. It's part of being alive.", "Give yourself three minutes of music, movement, or sensory delight."),
    ("A Little Alchemy", "Darling, we are choosing a partner, not adopting a renovation project. 😉", "Look for what someone consistently does, not just what they might become."),
    ("Love from Overflow", "You can be generous without making yourself responsible for everyone else's happiness.", "Notice one place where you can give from genuine abundance, not obligation."),
    ("The Wise Witch", "Your intuition deserves a seat at the table. So do the facts.", "Ask yourself: what have I actually observed, and what am I hoping is true?"),
    ("Your Love Vision", "A beautiful relationship is not just about being chosen. It's about choosing each other, again and again.", "Imagine one ordinary action that would make you feel cherished and free."),
    ("The Playful Princess", "You are allowed to enjoy being courted without surrendering your discernment.", "Practice expressing one simple preference with a smile."),
    ("Emotional Sovereignty", "Every feeling deserves to be heard. Not every feeling needs to be delivered.", "Give a strong feeling a little loving space before deciding what action it needs."),
]

def initialize(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS daily_alchemy (
        user_id INTEGER PRIMARY KEY,
        enabled INTEGER NOT NULL DEFAULT 0,
        timezone TEXT NOT NULL DEFAULT 'America/Toronto',
        last_sent_date TEXT,
        offered INTEGER NOT NULL DEFAULT 0
    )""")

def invitation():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Yes, enchant my mornings!", callback_data="daily:choose")],
        [InlineKeyboardButton("Maybe later 💜", callback_data="daily:later")],
    ])

def zones():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(name, callback_data="daily:tz:" + str(i))]
        for i, (name, _) in enumerate(ZONES)
    ] + [[InlineKeyboardButton("Not now", callback_data="daily:later")]])

def settings(enabled):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Change time zone", callback_data="daily:choose")],
        [InlineKeyboardButton("Pause daily messages" if enabled else "Enable daily messages", callback_data="daily:off" if enabled else "daily:choose")],
        [InlineKeyboardButton("My Alchemy Menu", callback_data="menu:open")],
    ])

def message_for(day):
    theme, insight, challenge = MESSAGES[day.toordinal() % len(MESSAGES)]
    return ("✨ DAILY LOVE ALCHEMY — " + theme + "\n\n" + insight
            + "\n\n🌷 Today's little experiment: " + challenge
            + "\n\nExplore further whenever you wish. /remaining · /dailyoff")

async def deliver(bot, db):
    while True:
        try:
            now = datetime.now(timezone.utc)
            with db() as conn:
                users = conn.execute("SELECT user_id,timezone,last_sent_date FROM daily_alchemy WHERE enabled=1").fetchall()
            for uid, zone, last in users:
                try:
                    local = now.astimezone(ZoneInfo(zone))
                    day = local.date().isoformat()
                    if local.hour < 8 or last == day:
                        continue
                    # Claim delivery first: restarts cannot double-send.
                    with db() as conn:
                        changed = conn.execute(
                            "UPDATE daily_alchemy SET last_sent_date=? WHERE user_id=? AND enabled=1 AND (last_sent_date IS NULL OR last_sent_date<>?)",
                            (day, uid, day)).rowcount
                    if changed:
                        await bot.send_message(uid, message_for(local.date()))
                except Exception:
                    log.exception("Daily delivery failed for user %s", uid)
        except Exception:
            log.exception("Daily scheduler iteration failed")
        await asyncio.sleep(60)
