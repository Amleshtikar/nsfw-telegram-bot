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

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
SE_USER = os.getenv("SE_USER")
SE_SECRET = os.getenv("SE_SECRET")

MUTE_TIME = 300

NSFW_WORDS = [
    "sex","porn","xxx","nude","adult",
    "fuck","chut","lund","boobs","pussy","randi"
]

BIO_LINK_KEYS = ["http", "https", "t.me", "telegram.me", "@", ".com", ".in"]

# ================= DATABASE =================
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
    bio_ok INTEGER,
    PRIMARY KEY (chat_id, user_id)
)
""")
db.commit()

# ================= HELPERS =================
def safe_name(user):
    return user.full_name.replace("<", "").replace(">", "")

def is_admin(context, chat_id, user_id):
    admins = context.bot.get_chat_administrators(chat_id)
    return user_id in [a.user.id for a in admins]

def contains_nsfw(text):
    if not text:
        return False
    return any(w in text.lower() for w in NSFW_WORDS)

def has_link_in_bio(context, user_id):
    try:
        bio = (context.bot.get_chat(user_id).bio or "").lower()
        return any(k in bio for k in BIO_LINK_KEYS)
    except:
        return False

def is_approved(chat_id, user_id):
    cur.execute(
        "SELECT 1 FROM approved WHERE chat_id=? AND user_id=?",
        (chat_id, user_id)
    )
    return cur.fetchone() is not None

def get_file_url(bot, file_id):
    f = bot.get_file(file_id)
    return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f.file_path}"

def is_porn_image(url):
    try:
        r = requests.post(
            "https://api.sightengine.com/1.0/check.json",
            params={
                "models": "nudity-2.1",
                "api_user": SE_USER,
                "api_secret": SE_SECRET
            },
            files={"media": requests.get(url, timeout=10).content},
            timeout=15
        )
        nud = r.json().get("nudity", {})
        score = nud.get("sexual_activity", 0) + nud.get("sexual_display", 0)
        return score >= 0.6
    except:
        return False

def is_porn_sticker_or_gif(msg):
    text = (msg.caption or "") + (msg.text or "")
    if contains_nsfw(text):
        return True

    if msg.sticker:
        if (msg.sticker.is_animated or msg.sticker.is_video) and msg.sticker.file_size:
            return msg.sticker.file_size > 180000

    if msg.animation:
        if msg.animation.file_size:
            return msg.animation.file_size > 250000

    return False

# ================= WARN / MUTE =================
def add_warn(chat_id, user_id):
    cur.execute(
        "SELECT count FROM warns WHERE chat_id=? AND user_id=?",
        (chat_id, user_id)
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE warns SET count=count+1 WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        db.commit()
        return row[0] + 1
    else:
        cur.execute(
            "INSERT INTO warns VALUES (?,?,1)",
            (chat_id, user_id)
        )
        db.commit()
        return 1

def reset_warn(chat_id, user_id):
    cur.execute(
        "DELETE FROM warns WHERE chat_id=? AND user_id=?",
        (chat_id, user_id)
    )
    db.commit()

# ================= ACTION =================
def punish(update, context):
    msg = update.message
    cid = msg.chat.id
    uid = msg.from_user.id

    try:
        msg.delete()
    except:
        pass

    count = add_warn(cid, uid)

    if count < 3:
        context.bot.send_message(
            cid,
            f"⚠️ Warning {count}/2\n"
            f"👤 {safe_name(msg.from_user)}\n"
            f"🆔 {uid}"
        )
    else:
        context.bot.restrict_chat_member(
            cid, uid,
            ChatPermissions(can_send_messages=False)
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔊 Unmute", callback_data=f"unmute:{uid}")]
        ])

        context.bot.send_message(
            cid,
            f"🔇 Muted 5 minutes\n"
            f"👤 {safe_name(msg.from_user)}\n"
            f"🆔 {uid}",
            reply_markup=kb
        )

        context.job_queue.run_once(
            unmute_job,
            MUTE_TIME,
            context={"chat_id": cid, "user_id": uid}
        )

def unmute_job(context):
    d = context.job.context
    context.bot.restrict_chat_member(
        d["chat_id"], d["user_id"],
        ChatPermissions(can_send_messages=True)
    )
    reset_warn(d["chat_id"], d["user_id"])

# ================= CALLBACK =================
def buttons(update, context):
    q = update.callback_query
    cid = q.message.chat.id
    q.answer()

    if not is_admin(context, cid, q.from_user.id):
        q.answer("❌ Only admin can use this", show_alert=True)
        return

    if q.data.startswith("unmute:"):
        uid = int(q.data.split(":")[1])
        context.bot.restrict_chat_member(
            cid, uid,
            ChatPermissions(can_send_messages=True)
        )
        reset_warn(cid, uid)
        q.edit_message_text("✅ User Unmuted")

# ================= COMMANDS =================
def start(update, context):
    update.message.reply_text("🛡 NSFW Protection Bot Active")

def approve(update, context):
    if not is_admin(context, update.effective_chat.id, update.effective_user.id):
        return
    if not update.message.reply_to_message:
        update.message.reply_text("Reply to user message")
        return

    user = update.message.reply_to_message.from_user
    bio_ok = 0 if has_link_in_bio(context, user.id) else 1

    cur.execute(
        "INSERT OR REPLACE INTO approved VALUES (?,?,?)",
        (update.effective_chat.id, user.id, bio_ok)
    )
    db.commit()

    update.message.reply_text(f"✅ Approved\n👤 {user.full_name}\n🆔 {user.id}")

def unapprove(update, context):
    if not is_admin(context, update.effective_chat.id, update.effective_user.id):
        return
    if not update.message.reply_to_message:
        update.message.reply_text("Reply to user message")
        return

    user = update.message.reply_to_message.from_user
    cur.execute(
        "DELETE FROM approved WHERE chat_id=? AND user_id=?",
        (update.effective_chat.id, user.id)
    )
    db.commit()

    update.message.reply_text(f"❌ Unapproved\n👤 {user.full_name}\n🆔 {user.id}")

# ================= MAIN HANDLER =================
def handler(update, context):
    msg = update.message
    cid = msg.chat.id
    uid = msg.from_user.id

    if is_approved(cid, uid):
        return

    if msg.text or msg.caption:
        if contains_nsfw(msg.text or msg.caption):
            punish(update, context)
            return

    if msg.photo:
        url = get_file_url(context.bot, msg.photo[-1].file_id)
        if is_porn_image(url):
            punish(update, context)
        return

    if msg.sticker or msg.animation:
        if is_porn_sticker_or_gif(msg):
            punish(update, context)
        return

    if msg.video:
        punish(update, context)

# ================= RUN =================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("approve", approve))
    dp.add_handler(CommandHandler("unapprove", unapprove))
    dp.add_handler(CallbackQueryHandler(buttons))
    dp.add_handler(MessageHandler(Filters.all, handler))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
