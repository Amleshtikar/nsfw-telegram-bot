import os
import sqlite3
import requests
from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
SE_USER = os.getenv("SE_USER")
SE_SECRET = os.getenv("SE_SECRET")

NSFW_WORDS = [
    "sex","porn","xxx","nude","adult",
    "fuck","chut","lund","boobs","pussy","randi"
]

MUTE_TIME = 300  # 5 minutes

# ================= DB =================
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS warns (
    chat_id INTEGER,
    user_id INTEGER,
    count INTEGER,
    PRIMARY KEY (chat_id, user_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS approved (
    chat_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (chat_id, user_id)
)
""")

db.commit()

# ================= HELPERS =================
def is_admin(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    admins = context.bot.get_chat_administrators(chat_id)
    return user_id in [a.user.id for a in admins]

def contains_nsfw(text):
    if not text:
        return False
    text = text.lower()
    return any(w in text for w in NSFW_WORDS)

def approved(chat_id, user_id):
    cur.execute("SELECT 1 FROM approved WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    return cur.fetchone() is not None

def add_warn(chat_id, user_id):
    cur.execute("SELECT count FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE warns SET count=count+1 WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        db.commit()
        return row[0] + 1
    else:
        cur.execute("INSERT INTO warns VALUES (?,?,1)", (chat_id, user_id))
        db.commit()
        return 1

def reset_warn(chat_id, user_id):
    cur.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    db.commit()

def get_file_url(bot, file_id):
    f = bot.get_file(file_id)
    return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f.file_path}"

def is_porn(url):
    try:
        r = requests.post(
            "https://api.sightengine.com/1.0/check.json",
            params={
                "models": "nudity-2.1",
                "api_user": SE_USER,
                "api_secret": SE_SECRET
            },
            files={"media": requests.get(url).content},
            timeout=20
        )
        nud = r.json().get("nudity", {})
        score = nud.get("sexual_activity",0)+nud.get("sexual_display",0)
        return score >= 0.6
    except:
        return False

# ================= ACTION =================
def punish(update, context):
    msg = update.message
    chat_id = msg.chat.id
    user_id = msg.from_user.id

    try: msg.delete()
    except: pass

    count = add_warn(chat_id, user_id)

    if count < 3:
        context.bot.send_message(chat_id, f"⚠️ Warning {count}/2\nNSFW not allowed")
    else:
        context.bot.restrict_chat_member(
            chat_id, user_id,
            ChatPermissions(can_send_messages=False)
        )
        context.bot.send_message(chat_id, "🔇 Muted for 5 minutes")

        context.job_queue.run_once(
            unmute_job, MUTE_TIME,
            context={"chat_id":chat_id,"user_id":user_id}
        )

def unmute_job(context):
    job = context.job.context
    context.bot.restrict_chat_member(
        job["chat_id"],
        job["user_id"],
        ChatPermissions(can_send_messages=True)
    )
    reset_warn(job["chat_id"], job["user_id"])

# ================= COMMANDS =================
def start(update, context):
    update.message.reply_text("🛡 NSFW AI Admin Bot Active")

def panel(update, context):
    if not is_admin(update, context): return
    kb = [
        [InlineKeyboardButton("✅ Approve", callback_data="approve"),
         InlineKeyboardButton("❌ Unapprove", callback_data="unapprove")],
        [InlineKeyboardButton("♻ Reset Warn", callback_data="reset")]
    ]
    update.message.reply_text("⚙ Admin Panel", reply_markup=InlineKeyboardMarkup(kb))

def buttons(update, context):
    q = update.callback_query
    q.answer()
    if not q.message.reply_to_message: return
    uid = q.message.reply_to_message.from_user.id
    cid = q.message.chat.id

    if q.data == "approve":
        cur.execute("INSERT OR IGNORE INTO approved VALUES (?,?)",(cid,uid))
        db.commit()
        q.edit_message_text("✅ User approved")

    elif q.data == "unapprove":
        cur.execute("DELETE FROM approved WHERE chat_id=? AND user_id=?",(cid,uid))
        db.commit()
        q.edit_message_text("❌ User unapproved")

    elif q.data == "reset":
        reset_warn(cid,uid)
        q.edit_message_text("♻ Warn reset")

# ================= HANDLER =================
def handler(update, context):
    msg = update.message
    cid = msg.chat.id
    uid = msg.from_user.id

    if approved(cid,uid):
        return

    if (msg.text and contains_nsfw(msg.text)) or (msg.caption and contains_nsfw(msg.caption)):
        punish(update,context); return

    if msg.photo:
        if is_porn(get_file_url(context.bot,msg.photo[-1].file_id)):
            punish(update,context)

    if msg.video or msg.animation:
        f = msg.video or msg.animation
        if is_porn(get_file_url(context.bot,f.file_id)):
            punish(update,context)

    if msg.sticker:
        if contains_nsfw(msg.sticker.emoji or ""):
            punish(update,context)

    if msg.contact:
        punish(update,context)

# ================= MAIN =================
def main():
    up = Updater(BOT_TOKEN, use_context=True)
    dp = up.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("panel", panel))
    dp.add_handler(CallbackQueryHandler(buttons))
    dp.add_handler(MessageHandler(Filters.all, handler))

    up.start_polling()
    up.idle()

if __name__ == "__main__":
    main()
