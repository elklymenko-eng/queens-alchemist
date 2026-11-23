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

    ("A Little Mystery", "You don't need to reveal your entire life story over three cups of coffee. Attraction loves discovery. Let someone get to know you one delightful chapter at a time.", "Be curious. Leave a little room for the next conversation."),
    ("Your Inner Critic Has Opinions", "Your inner critic has opinions. Lots of them. But having an opinion doesn't make her the CEO of your life. You can hear the frightened part of you without handing her the steering wheel.", "When an old fear speaks, ask: Is this wisdom—or an old story?"),
    ("The World Will Survive", "The world will survive if you relax. Seriously. You don't have to hold everything together to deserve a beautiful life. Sometimes your most productive decision is to stop producing.", "Enjoy something today without turning it into an accomplishment."),
    ("Love Is Already Here", "What if love isn't something you have to chase? Your life may already be full of opportunities to experience it—in friendship, beauty, laughter, generosity, and connection. Romantic love can grow from that fullness rather than being asked to create it.", "Notice three ways love is already present in your world."),
    ("Stop Auditioning", "Stop auditioning. You're not applying for the position of Girlfriend. Dating is an encounter between two interesting humans, not an interview where one person decides the other's worth.", "Replace 'Will they like me?' with 'Am I enjoying this?'"),
    ("More Than a Talking Head", "Your body was made for more than carrying your head around. It can dance, stretch, taste, breathe, laugh, and experience extraordinary pleasure in ordinary moments.", "Put on a song you love. Let your body decide what happens next."),
    ("Your Priestess Speaks", "Not every answer arrives through thinking. Some become clear when the noise settles.", "Give yourself a quiet moment without reaching for your phone. Listen to what you already know."),
    ("Your Wild Woman Speaks", "When was the last time you did something simply because it made you feel alive?", "Break one harmless little routine. Take the scenic route. Dance unexpectedly. Follow your curiosity."),
    ("Your Inner Mother Speaks", "You don't need to be exhausted to deserve tenderness. And you don't need a good reason to take care of yourself.", "Offer yourself the same warmth you'd give someone you deeply love."),
    ("Your Wise Witch Speaks", "Some rules were handed to you before you were old enough to question them. You are allowed to reconsider.", "Notice one old 'should' and ask whether it still belongs in your life."),
    ("Your Lover Speaks", "Darling, life is not meant to be admired from behind a window.", "Experience something delicious with your senses. Taste slowly. Feel the sunshine. Let pleasure have your full attention."),
    ("Your Princess Speaks", "You don't have to be the responsible adult every single minute.", "Let yourself be delighted by something small, silly, beautiful, or completely unnecessary."),
    ("Your Warrior Speaks", "Your strength is not measured by how much you can endure. Sometimes courage means choosing a different direction.", "Use your strength in service of something you genuinely desire."),
    ("Your Jester Speaks", "Breaking news: You are officially allowed to take life a little less seriously.", "Find one reason to laugh at the absurdity of being human."),
    ("Your Queen Speaks", "You don't have to silence the parts of you that disagree. Your heart can want adventure while another part longs for comfort.", "Make room for both. Wholeness is not the absence of contradictions."),
    ("Your Inner Guardian Speaks", "You can relax. I am here to help you make wise choices, not to criticize every move.", "Let discernment support your freedom instead of restricting it."),
    ("The Lover's Invitation", "What if you stopped waiting for someone else to bring romance into your life?", "Make one ordinary moment feel special. Beautiful music, fresh flowers, candlelight—just because."),
    ("The Wild Woman's Permission Slip", "You are allowed to change your mind. To explore. To discover a new side of yourself.", "Ask: What would I try if I didn't need to explain myself to everyone?"),
    ("The Priestess and the Queen", "Your intuition can whisper. Your wisdom can investigate. You don't have to choose between them.", "Honor both what you feel and what you know."),
    ("The Queen's Reminder", "You are not a project that needs endless improvement before life can begin.", "Live a little of the beautiful life you've been preparing yourself for."),
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
                    if local.hour != 8 or last == day:
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
