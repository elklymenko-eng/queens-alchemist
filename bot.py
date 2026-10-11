import os, json, sqlite3, logging
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('queens_alchemist')
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_KEY = os.getenv('OPENAI_API_KEY')
MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
ALLOWED = {int(v.strip()) for v in os.getenv('ALLOWED_USER_IDS', '').split(',') if v.strip()}
DATA_DIR = Path(os.getenv('DATA_DIR', './data'))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB = DATA_DIR / 'beta.sqlite3'
BASE = Path(__file__).parent
PRACTICES = json.loads((BASE / 'practices.json').read_text())
KNOWLEDGE = (BASE / 'knowledge.md').read_text()
AI = AsyncOpenAI(api_key=API_KEY) if API_KEY else None

SYSTEM = '''You are The Queen's Alchemist, an AI coaching companion grounded in Elena's Queen's Alchemy teachings. You are not Elena. Speak warmly, perceptively, with elegant wit when natural, but not floridly or at excessive length. Meet the actual question before going deeper. Usually ask one intelligent question at a time; do not leap to archetype labels or spiritual causation. In early conversation, learn her situation and desire, then give concise reflection and a grounded next step. If appropriate, offer exactly one relevant practice and its real URL from the catalogue, never invent links. Ask permission before deeper inner-child work. Do not make health or hormone claims as established facts without evidence. Avoid dependency and repetitive upselling. Never promise guaranteed attraction or commitment. Make practical room for a partner's observable behavior and the woman's own agency. You are coaching/education, not therapy. If user reports immediate danger, self-harm, abuse or coercion, prioritize safety and human support. Do not collect unnecessary personal identifiers. You can offer interactive journaling one prompt at a time; let her skip or stop. Do not imply you have watched the linked videos.\n\nKNOWLEDGE:\n'''+KNOWLEDGE+'\n\nPRACTICE CATALOGUE:\n'+json.dumps(PRACTICES,ensure_ascii=False)


def db():
    c = sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS messages (user_id INTEGER, role TEXT, content TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)')
    c.execute('CREATE TABLE IF NOT EXISTS feedback (user_id INTEGER, rating TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)')
    c.commit()
    return c


def authorized(update: Update):
    return bool(ALLOWED) and update.effective_user.id in ALLOWED

async def gate(update: Update):
    if authorized(update): return True
    await update.effective_message.reply_text('The Queen’s Alchemist is currently a private beta. Your Telegram ID is '+str(update.effective_user.id)+'. Send this numeric ID to Elena to request access. Please do not send any personal relationship details until invited.')
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await gate(update): return
    await update.message.reply_text('👑 Welcome to The Queen’s Alchemist — Elena’s AI coaching companion for conscious love, dating and feminine embodiment.\n\nI’m AI, not Elena or a therapist. Please avoid sharing identifying or highly sensitive details. Beta conversations are processed by our AI provider and stored by the bot operator for continuity; use /reset to erase your chat history in this beta database.\n\nWhere are you in your love life?', reply_markup=InlineKeyboardMarkup([
      [InlineKeyboardButton('Single / Dating',callback_data='status:Single or dating'),InlineKeyboardButton('In a relationship',callback_data='status:In a relationship')],
      [InlineKeyboardButton('Situationship / Complicated',callback_data='status:Situationship or complicated')],
      [InlineKeyboardButton('Breakup / Healing',callback_data='status:Breakup or healing'),InlineKeyboardButton('Something else',callback_data='status:Something else')]
    ]))

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await gate(update): return
    value = q.data.split(':',1)[1]
    with db() as c: c.execute('INSERT INTO messages (user_id,role,content) VALUES (?,?,?)',(q.from_user.id,'user','My relationship status: '+value))
    await q.message.reply_text('What is happening in your love life that you most want help with right now?')

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await gate(update): return
    msg = update.message.text.strip()
    if not msg: return
    uid = update.effective_user.id
    if len(msg)>3500:
        await update.message.reply_text('Could you send a shorter message (under 3,500 characters)?')
        return
    with db() as c:
        history=c.execute('SELECT role,content FROM messages WHERE user_id=? ORDER BY ts DESC,rowid DESC LIMIT 16',(uid,)).fetchall()[::-1]
    await update.message.chat.send_action('typing')
    try:
        response = await AI.responses.create(model=MODEL, instructions=SYSTEM, input=[{'role':r,'content':t} for r,t in history]+[{'role':'user','content':msg}], max_output_tokens=700, store=False)
        answer = response.output_text.strip() or 'Could you say a little more about that?'
    except Exception:
        log.exception('AI request failed')
        await update.message.reply_text('I’m having trouble responding right now. Please try again shortly.')
        return
    with db() as c:
        c.execute('INSERT INTO messages (user_id,role,content) VALUES (?,?,?)',(uid,'user',msg))
        c.execute('INSERT INTO messages (user_id,role,content) VALUES (?,?,?)',(uid,'assistant',answer))
    for i in range(0,len(answer),3800): await update.message.reply_text(answer[i:i+3800],disable_web_page_preview=True)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await gate(update): return
    with db() as c: c.execute('DELETE FROM messages WHERE user_id=?',(update.effective_user.id,))
    await update.message.reply_text('Your stored beta conversation history has been deleted. You can start fresh with /start.')

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await gate(update): return
    await update.message.reply_text('How helpful has this conversation been?',reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❤️ Very',callback_data='rate:very'),InlineKeyboardButton('🙂 Somewhat',callback_data='rate:somewhat'),InlineKeyboardButton('👎 Not really',callback_data='rate:not_really')]]))

async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    if not await gate(update): return
    with db() as c: c.execute('INSERT INTO feedback (user_id,rating) VALUES (?,?)',(q.from_user.id,q.data.split(':',1)[1]))
    await q.message.reply_text('Thank you! Your feedback helps Elena refine the Alchemist.')

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Your Telegram numeric user ID: '+str(update.effective_user.id))

if __name__ == '__main__':
    if not TOKEN or not API_KEY: raise RuntimeError('Set TELEGRAM_BOT_TOKEN and OPENAI_API_KEY in hosting environment')
    if not ALLOWED: log.warning('No users are authorized yet; /id remains available.')
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('id',id_cmd))
    app.add_handler(CommandHandler('start',start))
    app.add_handler(CommandHandler('reset',reset))
    app.add_handler(CommandHandler('feedback',feedback))
    app.add_handler(CallbackQueryHandler(status,pattern=r'^status:'))
    app.add_handler(CallbackQueryHandler(rate,pattern=r'^rate:'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,chat))
    app.run_polling(drop_pending_updates=True)
