import os, json, sqlite3, logging, asyncio
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
FREE_REPLIES = 10
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
        "✨ Your first 10 personalized AI replies are my gift to you. This discovery journey doesn't use any of them." + "\n\n" +
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
    with db() as c:
        if kind == "s" and idx < len(STATUS):
            c.execute("UPDATE profiles SET status=?,stage=1 WHERE user_id=?", (STATUS[idx][0], uid))
            await q.message.reply_text(
                "What keeps happening in your love life? Choose the one that feels closest. "
                "We'll explore it together—this isn't a diagnosis.",
                reply_markup=buttons(PATTERNS, "p:"))
        elif kind == "p" and idx < len(PATTERNS):
            c.execute("UPDATE profiles SET patterns=?,stage=2 WHERE user_id=?", (PATTERNS[idx], uid))
            await q.message.reply_text(
                "You aren't just one archetype. Princess, Lover, Mother, Warrior, Priestess and other aspects "
                "can all be active. Your Queen holds them with compassion and chooses with discernment.\n\n"
                "What would you most like to explore?",
                reply_markup=buttons(GOALS, "g:"))
        elif kind == "g" and idx < len(GOALS):
            c.execute("UPDATE profiles SET goal=?,stage=3 WHERE user_id=?", (GOALS[idx], uid))
            await q.message.reply_text(
                "What shall I call you? A first name or nickname is optional.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Skip", callback_data="n:0")]]))
        elif kind == "n":
            c.execute("UPDATE profiles SET stage=4 WHERE user_id=?", (uid,))
            await q.message.reply_text(
                "Lovely. Now tell me a little about what's happening in your love life. "
                "Or just say 'start' and we'll explore your choices together. "
                "Your first AI reply begins when you send a message.")
        else:
            return

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await gate(update): return
    msg = (update.effective_message.text or "").strip()
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
        if stage < 3:
            await update.effective_message.reply_text("Send /start to begin the free discovery quiz.")
            return
        if uid not in OWNERS and used >= FREE_REPLIES:
            await update.effective_message.reply_text(
                "👑 You've enjoyed your 10 free Alchemist replies. Thank you for exploring! "
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
                max_output_tokens=700, store=False)
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
        if uid not in OWNERS and used + 1 in (3, 8):
            await update.effective_message.reply_text(
                "A little Queen's Alchemist check-in: how helpful has this felt so far? "
                "This doesn't use a free reply.",
                reply_markup=buttons(["❤️ Very", "🙂 Somewhat", "👎 Not really", "✍️ Share a thought"], "f:"))
        if uid not in OWNERS and remaining == 1:
            await update.effective_message.reply_text(
                "You've reached the end of your 10 free AI replies. "
                "Thank you for being part of our beta! Send /feedback to share your experience.")
        elif uid not in OWNERS and remaining in (6, 3):
            await update.effective_message.reply_text(
                "👑 " + str(remaining-1) + " free AI replies left. Continue whenever you're ready.")

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
                        else str(max(0, FREE_REPLIES-used)) + " of 10 free AI replies remaining") + ".")

if __name__ == "__main__":
    if not TOKEN or not API_KEY: raise RuntimeError("Set TELEGRAM_BOT_TOKEN and OPENAI_API_KEY")
    if not BETA_OPEN and not ALLOWED and not OWNERS: log.warning("No users authorized. Use BETA_OPEN=true for an open tester beta.")
    app = Application.builder().token(TOKEN).build()
    for cmd, fn in [("id", id_cmd), ("start", start), ("reset", reset), ("feedback", feedback), ("remaining", remaining_cmd)]:
        app.add_handler(CommandHandler(cmd, fn))
    app.add_handler(CallbackQueryHandler(onboarding, pattern=r"^(s|p|g|n):"))
    app.add_handler(CallbackQueryHandler(rate, pattern=r"^f:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.run_polling(drop_pending_updates=True)
