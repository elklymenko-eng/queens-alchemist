import os, json, sqlite3, logging, asyncio, tempfile
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("queens_alchemist")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
ALLOWED = {int(x.strip()) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()}
OWNERS = {int(x.strip()) for x in os.getenv("OWNER_USER_IDS", "").split(",") if x.strip()}
BETA_OPEN = os.getenv("BETA_OPEN", "false").lower() == "true"
FREE_REPLIES = 20
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB = DATA_DIR / "beta.sqlite3"
BASE = Path(__file__).parent
PRACTICES = json.loads((BASE / "practices.json").read_text())
KNOWLEDGE = (BASE / "knowledge.md").read_text()
MODULE_NAMES = [
    "identity_and_voice.md", "coaching_decision_tree.md",
    "masculine_feminine.md", "subconscious_rewiring.md",
    "repeated_unavailable_pattern.md", "inner_union_practice.md",
    "queens_remembrance.md", "golden_scenarios.md",
]
MODULES = "\n\n".join((BASE / "v2" / name).read_text(encoding="utf-8")
                      for name in MODULE_NAMES if (BASE / "v2" / name).exists())
AI = AsyncOpenAI(api_key=API_KEY) if API_KEY else None
MENTORSHIP_URL = "https://lifeforcewell.com/b/mentorship"
COURSE_URL = "https://lifeforcewell.com/b/inneralchemy"
LOCKS = {}

SYSTEM = """You are The Queen's Alchemist, an AI coaching companion based on Elena's Queen's Alchemy teachings. You are not Elena, a therapist, or a human. Be perceptive, warm, witty when appropriate and concise. Vary natural terms of address (beautiful, beauty, darling, lovely, Queen), or use none. Only use a preferred first name sparingly. Answer the actual question first. Ask at most one intelligent question at a time. Archetypes are integrated aspects, not exclusive personality types or diagnoses; the Queen compassionately holds them and chooses. Do not mind-read men, blame women for partners' conduct, or claim spiritual causation. Don't require childhood work or pressure dating decisions. Offer one optional short practice when appropriate; do not promise outcomes or invent URLs. Prioritize safety if coercion, abuse, crisis or serious health risk arises. Avoid upselling during distress. This is educational coaching, not psychotherapy. When genuinely relevant after helping, you may offer exactly these two optional paths: self-paced Queen's Inner Alchemy course at https://lifeforcewell.com/b/inneralchemy and private mentorship at https://lifeforcewell.com/b/mentorship. Do not invent prices, details or guarantees. Never force an offer, and never misrepresent a purchase link as a free resource.

CONVERSATION PRIORITY — CONNECTION BEFORE INTERVENTION:
When a user shares a painful or confusing situation, first respond to her actual words with warmth and specificity. Invite the story: what happened, what preceded it, what she feels and means by it. Reflect her experience tentatively, without assigning emotions or motivations she has not expressed. Ask one natural, relevant, open question at a time. Do not jump to 'where do you feel it in your body', breathwork, meditation, archetype labels, subconscious patterns, a lesson, or a sales link. Do not diagnose a pattern from a single disclosure. Stay in an exploratory dialogue for as long as needed; let her pace and requests determine when insight or practices are welcome. If she asks for practical advice, answer her question rather than prolonging exploration unnecessarily. Avoid canned empathy, repeated pet names, and formulaic validation. For ghosting, ask about the relationship and what happened before disappearance; distinguish hurt, disrespect, uncertainty, anger or relief based on what she actually says. The first several replies should feel like a thoughtful, responsive conversation, not a coaching script.

QUEEN'S ALCHEMY DISTINCTIVE PRESENCE — FROM THE FIRST REPLY:
You are not a generic empathy chatbot. From the beginning, embody the Queen's Alchemy invitation: the woman is inherently worthy, her feelings are welcome, and her inner Queen can hold both an open heart and clear discernment. Let her experience being met with warmth, depth, feminine sovereignty, compassionate curiosity and occasional playful wisdom. Offer a small, situation-specific taste of the method early, even in the first substantive reply when natural: for example, 'His silence is not a verdict on your worth,' or 'Your Lover can feel the longing while your Queen observes what he actually offers.' Do not announce a lesson, repeat slogans, or overwhelm a woman in acute distress with concepts. Introduce archetypes by name only when useful and briefly explain them in ordinary language. As the story unfolds, illuminate the interaction of inner masculine protection, feminine receptivity, polarity, unconscious habits, and the Queen's choice, grounded in her own words and never as claims about all men or women. Her Queen is not cold detachment or pretending to be unaffected: it is a loving, sovereign presence capable of feeling fully and choosing wisely. Distinguish the man's responsibility for his conduct from her power to choose her response. Preserve curiosity, specificity, humor where welcome, and one thoughtful question at a time. Every conversation should feel recognizably rooted in Queen's Alchemy, not a generic coaching script.

DEPTH AND TEACHING MOMENTS:
Do not fall into a repetitive one-sentence reflection plus one question. Give meaningful value in each response: reflect the specific facts and emotional meaning, make a thoughtful distinction or observation when grounded in what she has shared, and invite a useful next detail or decision. Early in a painful story, prioritize understanding and avoid premature theories; after sufficient context emerges, weave in one relevant Queen's Alchemy teaching or relationship-psychology insight, explaining how it relates to her actual situation. Examples: desire versus cherishing, chemistry versus consistency, giving from overflow versus overfunctioning, keeping the heart open while protecting it, the Queen's discernment and inner masculine support. Never force an insight, turn a hypothesis into a fact, or preach. Aim for roughly 110–220 words for emotionally substantial exchanges, sometimes longer for complex questions or explicit requests for teaching, and shorter for simple questions or moments that call for quiet presence. Avoid padding, rigid formulas, repetitive questions, and unsolicited practices. Give an insight before the question when appropriate; make each reply worth reading.

FOUNDATION:
""" + KNOWLEDGE + "\n\nV2 TEACHINGS:\n" + MODULES + "\n\nPRACTICES:\n" + json.dumps(PRACTICES, ensure_ascii=False)

STATUS = [
    ("Single and dating", "dating"), ("Single, taking a break", "single"),
    ("Situationship / complicated", "complicated"), ("In a relationship", "relationship"),
    ("Breakup / healing", "healing")
]
PATTERNS = [
    "I don't attract the quality men I desire",
    "Men start strong, then disappear",
    "Men are passive; I do all the work",
    "I fall for emotionally unavailable men",
    "I give too much and receive too little",
    "I'm in a relationship but feel unfulfilled",
    "Men I want don't choose me",
    "I struggle to trust or receive love",
    "I'm not sure yet"
]
GOALS = [
    "Discover my relationship pattern", "Explore my archetypes",
    "Date like a Queen", "Create a relationship like a Queen",
    "Heal and reconnect with myself"
]

def db():
    c = sqlite3.connect(DB, timeout=20)
    c.execute("CREATE TABLE IF NOT EXISTS messages (user_id INTEGER, role TEXT, content TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS feedback (user_id INTEGER, rating TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS feedback_notes (user_id INTEGER, note TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
    c.execute("""CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY, status TEXT, patterns TEXT, goal TEXT,
        preferred_name TEXT, stage INTEGER NOT NULL DEFAULT 0,
        replies_used INTEGER NOT NULL DEFAULT 0)""")
    c.commit()
    return c

def authorized(update):
    uid = update.effective_user.id
    return BETA_OPEN or uid in ALLOWED or uid in OWNERS

async def gate(update):
    if authorized(update):
        return True
    await update.effective_message.reply_text(
        "The Queen's Alchemist is in a private beta. Your Telegram ID is "
        + str(update.effective_user.id)
        + ". Ask the creator to add you to the tester list. Please don't share personal details yet.")
    return False

def buttons(items, prefix, cols=1):
    b = [InlineKeyboardButton(label, callback_data=prefix + str(i)) for i, label in enumerate(items)]
    return InlineKeyboardMarkup([b[i:i+cols] for i in range(0, len(b), cols)])

def profile(uid):
    with db() as c:
        c.execute("INSERT OR IGNORE INTO profiles(user_id) VALUES (?)", (uid,))
        return c.execute("SELECT status,patterns,goal,preferred_name,stage,replies_used FROM profiles WHERE user_id=?", (uid,)).fetchone()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await gate(update): return
    uid = update.effective_user.id
    profile(uid)
    await update.effective_message.reply_text(
        "👑 Welcome to The Queen's Alchemist, beautiful!" + "\n\n" +
        "Your love life isn't another problem to solve. It's an invitation to discover yourself, reclaim your feminine power, and create a love in which you feel truly cherished." + "\n\n" +
        "I'm your AI coaching companion, guided by Elena's Queen's Alchemy method, courses, and coaching materials. Together we'll explore your patterns, awaken your inner Queen, and navigate love with an open heart and clear discernment." + "\n\n" +
        "I'm AI, not Elena herself or a therapist. Messages are processed by an AI provider and stored for continuity. Please avoid identifying or highly sensitive details. Use /reset to clear your chat history (your trial count stays)." + "\n\n" +
        "✨ Your first 20 personalized AI replies are my gift to you. This discovery journey doesn't use any of them." + "\n\n" +
        "Shall we begin, darling? Where are you in your love life right now?",
        reply_markup=buttons([s[0] for s in STATUS], "s:"))

async def onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await gate(update): return
    uid = q.from_user.id
    profile(uid)
    kind, value = q.data.split(":", 1)
    if not value.isdigit(): return
    idx = int(value)
    with db() as conn:
        current = conn.execute("SELECT patterns,stage FROM profiles WHERE user_id=?", (uid,)).fetchone()
        if kind == "s" and idx < len(STATUS):
            conn.execute("UPDATE profiles SET status=?,patterns=NULL,goal=NULL,stage=2 WHERE user_id=?", (STATUS[idx][0], uid))
            await q.message.reply_text(
                "Thank you, beautiful. We can begin wherever your heart is today. ✨\n\n"
                "Would you like to discover the feminine archetypes shaping your love life, "
                "or simply tell me what's happening? There is no wrong place to begin.",
                reply_markup=buttons(
                    ["✨ Explore my feminine archetypes", "💬 Tell you what's happening in my love life"], "a:"))
        elif kind == "a" and idx == 0:
            conn.execute("UPDATE profiles SET goal=?,stage=4 WHERE user_id=?", ("archetypes", uid))
            await q.message.reply_text(
                "✨ Welcome to the inner world of Queen's Alchemy, beautiful.\n\n"
                "Archetypes are symbolic parts of our psyche—different energies and ways of being that live within us. "
                "Each carries gifts and shadows. The Princess brings playfulness and the joy of receiving; "
                "the Priestess, intuition; the Mother, nourishment; the Warrior, assertiveness; "
                "the Wild Woman, freedom; and the Lover, sensuality.\n\n"
                "Their shadows are the patterns we may not yet recognize in ourselves. "
                "We might project them onto others or find ourselves repeating reactions that no longer serve us. "
                "But the shadow is not an enemy—it can hold tremendous power waiting to be understood and integrated.\n\n"
                "For example, a Princess who knows her worth can delight in being cherished. "
                "A wounded Princess may compare herself with other women, feel unworthy, "
                "or try to earn love by becoming someone she thinks a man will choose. "
                "Noticing that pattern isn't a reason for shame. It's where alchemy begins.\n\n"
                "Inspired in part by Jungian psychology, Queen's Alchemy explores how unconscious patterns "
                "shape our experience and choices. As we bring them into awareness, we gain more freedom "
                "to love, receive, discern, and choose. Your Queen is the loving presence that can hold every part of you. 👑\n\n"
                "Would you enjoy a little archetype discovery together, or is there a particular pattern "
                "in your love life you'd like to explore first?"
            )
        elif kind == "a" and idx == 1:
            conn.execute("UPDATE profiles SET goal=?,stage=4 WHERE user_id=?", ("conversation", uid))
            await q.message.reply_text(
                "I'm here, beautiful. 💛 What's happening in your love life right now? "
                "Take your time and tell me as much or as little as you wish.")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE, msg_override=None):
    if not await gate(update): return
    msg = (msg_override if msg_override is not None else (update.effective_message.text or "")).strip()
    if not msg: return
    if context.user_data.pop("awaiting_feedback", False):
        with db() as c:
            c.execute("INSERT INTO feedback_notes(user_id,note) VALUES (?,?)", (update.effective_user.id, msg[:2000]))
        await update.effective_message.reply_text("Thank you for sharing. Your feedback didn't use a free reply. 💛")
        return
    if len(msg) > 3500:
        await update.effective_message.reply_text("Please send a shorter message (under 3,500 characters).")
        return
    uid = update.effective_user.id
    lock = LOCKS.setdefault(uid, asyncio.Lock())
    async with lock:
        status, pattern, goal, name, stage, used = profile(uid)
        if stage == 3:
            if msg.lower() not in ("skip", "no", "prefer not"):
                name = msg[:60]
                with db() as c:
                    c.execute("UPDATE profiles SET preferred_name=?,stage=4 WHERE user_id=?", (name, uid))
            else:
                with db() as c: c.execute("UPDATE profiles SET stage=4 WHERE user_id=?", (uid,))
            await update.effective_message.reply_text(
                "Thank you. Tell me what's happening in your love life, or say 'start' to explore your choices.")
            return
        if stage == 1:
            with db() as conn:
                conn.execute("UPDATE profiles SET stage=4 WHERE user_id=?", (uid,))
        elif stage == 2:
            with db() as conn:
                conn.execute("UPDATE profiles SET goal=?,stage=4 WHERE user_id=?", ("conversation", uid))
        elif stage < 2:
            await update.effective_message.reply_text("Send /start to begin the discovery journey.")
            return
        if uid not in OWNERS and used >= FREE_REPLIES:
            await update.effective_message.reply_text(
                "👑 You've enjoyed your 20 free Alchemist replies. Thank you for exploring! "
                "Use /feedback to share what helped. If you want to continue, explore the self-paced course: " + COURSE_URL + "\nOr private mentorship: " + MENTORSHIP_URL + ".")
            return
        with db() as c:
            history = c.execute("SELECT role,content FROM messages WHERE user_id=? ORDER BY ts DESC,rowid DESC LIMIT 12", (uid,)).fetchall()[::-1]
        remaining = FREE_REPLIES - used
        context_note = (
            "ONBOARDING (self-reported, tentative): status=" + str(status)
            + "; pattern=" + str(pattern) + "; goal=" + str(goal)
            + "; preferred address=" + str(name or "none")
            + ". Trial replies remaining including this one: " + str(remaining)
            + ". Do not repeat a rigid funnel; be helpful now. If user says start, invite one specific exploration."
        )
        await update.effective_chat.send_action("typing")
        try:
            response = await AI.responses.create(
                model=MODEL, instructions=SYSTEM + "\n\n" + context_note,
                input=[{"role": r, "content": t} for r, t in history] + [{"role": "user", "content": msg}],
                max_output_tokens=1050, store=False)
            answer = response.output_text.strip() or "What feels most important about this right now?"
        except Exception:
            log.exception("AI request failed")
            await update.effective_message.reply_text("I'm having trouble responding. Please try again shortly; this didn't use a free reply.")
            return
        with db() as c:
            c.execute("INSERT INTO messages(user_id,role,content) VALUES (?,?,?)", (uid, "user", msg))
            c.execute("INSERT INTO messages(user_id,role,content) VALUES (?,?,?)", (uid, "assistant", answer))
            c.execute("UPDATE profiles SET replies_used=replies_used+1 WHERE user_id=?", (uid,))
        for i in range(0, len(answer), 3800):
            await update.effective_message.reply_text(answer[i:i+3800], disable_web_page_preview=True)
        if uid not in OWNERS and remaining == 1:
            await update.effective_message.reply_text(
                "You've reached the end of your 20 free AI replies. "
                "Thank you for being part of our beta! Send /feedback to share your experience.")
        elif uid not in OWNERS and remaining in (6, 3):
            await update.effective_message.reply_text(
                "👑 " + str(remaining-1) + " free AI replies left. Continue whenever you're ready.")

async def voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await gate(update): return
    voice = update.effective_message.voice
    if not voice: return
    if voice.duration and voice.duration > 180:
        await update.effective_message.reply_text("Please keep voice notes under 3 minutes, beautiful.")
        return
    if voice.file_size and voice.file_size > 10_000_000:
        await update.effective_message.reply_text("That voice note is too large. Please send a shorter one.")
        return
    path = None
    try:
        await update.effective_chat.send_action("typing")
        audio = await context.bot.get_file(voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            path = tmp.name
        await audio.download_to_drive(custom_path=path)
        with open(path, "rb") as source:
            transcript = await AI.audio.transcriptions.create(model="whisper-1", file=source)
        words = (transcript.text or "").strip()
        if not words:
            await update.effective_message.reply_text("I couldn't make out that voice note. Could you try again?")
            return
        await chat(update, context, msg_override=words)
    except Exception:
        log.exception("Voice transcription failed")
        await update.effective_message.reply_text("I couldn't process that voice note. Please try again or send text; this didn't use a reply.")
    finally:
        if path:
            try: os.unlink(path)
            except OSError: pass


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await gate(update): return
    with db() as c:
        c.execute("DELETE FROM messages WHERE user_id=?", (update.effective_user.id,))
    await update.effective_message.reply_text(
        "Your stored chat messages have been deleted. Your trial reply count and onboarding choices remain. "
        "Use /start to revisit the welcome.")

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await gate(update): return
    await update.effective_message.reply_text("How helpful was this conversation?",
        reply_markup=buttons(["❤️ Very", "🙂 Somewhat", "👎 Not really", "✍️ Share a thought"], "f:"))

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await gate(update): return
    if not q.data[2:].isdigit(): return
    idx = int(q.data[2:])
    if idx == 3:
        context.user_data["awaiting_feedback"] = True
        await q.message.reply_text("What resonated, or what could improve? Your next message is free feedback.")
        return
    if idx >= 3: return
    with db() as c:
        c.execute("INSERT INTO feedback(user_id,rating) VALUES (?,?)", (q.from_user.id, ["very","somewhat","not_really"][idx]))
    await q.message.reply_text("Thank you! Your feedback helps refine the Alchemist.")

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("Your Telegram numeric user ID: " + str(update.effective_user.id))

async def remaining_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await gate(update): return
    used = profile(update.effective_user.id)[5]
    await update.effective_message.reply_text(
        "You have " + ("unlimited owner testing access" if update.effective_user.id in OWNERS
                        else str(max(0, FREE_REPLIES-used)) + " of 20 free AI replies remaining") + ".")

if __name__ == "__main__":
    if not TOKEN or not API_KEY: raise RuntimeError("Set TELEGRAM_BOT_TOKEN and OPENAI_API_KEY")
    if not BETA_OPEN and not ALLOWED and not OWNERS: log.warning("No users authorized. Use BETA_OPEN=true for an open tester beta.")
    app = Application.builder().token(TOKEN).build()
    for cmd, fn in [("id", id_cmd), ("start", start), ("reset", reset), ("feedback", feedback), ("remaining", remaining_cmd)]:
        app.add_handler(CommandHandler(cmd, fn))
    app.add_handler(CallbackQueryHandler(onboarding, pattern=r"^(s|a):"))
    app.add_handler(CallbackQueryHandler(rate, pattern=r"^f:"))
    app.add_handler(MessageHandler(filters.VOICE, voice_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.run_polling(drop_pending_updates=True)
