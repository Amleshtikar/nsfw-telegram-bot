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

# bio_ok = 1 → approve time pe bio clean
# bio_ok = 0 → approve time pe bio me link tha
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

def is_admin(update, context):
    admins = context.bot.get_chat_administrators(update.effective_chat.id)
    return update.effective_user.id in [a.user.id for a in admins]

def contains_nsfw(text):
    if not text:
        return False
    text = text.lower()
    return any(w in text for w in NSFW_WORDS)

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

def auto_unapprove_if_bio_link(context, chat_id, user_id):
    cur.execute(
        "SELECT bio_ok FROM approved WHERE chat_id=? AND user_id=?",
        (chat_id, user_id)
    )
    row = cur.fetchone()
    if not row:
        return

    bio_ok_at_approve = row[0]

    # approved time pe bio clean tha, baad me link add hua
    if bio_ok_at_approve == 1 and has_link_in_bio(context, user_id):
        cur.execute(
            "DELETE FROM approved WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        db.commit()

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
            cid,
            uid,
            ChatPermissions(can_send_messages=False)
        )
        context.bot.send_message(
            cid,
            f"🔇 Muted 5 minutes\n"
            f"👤 {safe_name(msg.from_user)}\n"
            f"🆔 {uid}"
        )
        context.job_queue.run_once(
            unmute_job,
            MUTE_TIME,
            context={"chat_id": cid, "user_id": uid}
        )

def unmute_job(context):
    d = context.job.context
    context.bot.restrict_chat_member(
        d["chat_id"],
        d["user_id"],
        ChatPermissions(can_send_messages=True)
    )
    reset_warn(d["chat_id"], d["user_id"])

# ================= COMMANDS =================
def start(update, context):
    update.message.reply_text("🛡 NSFW Protection Bot Active")

def panel(update, context):
    if not is_admin(update, context):
        return

    if not update.message.reply_to_message:
        update.message.reply_text("Reply to user message then /panel")
        return

    user = update.message.reply_to_message.from_user
    context.user_data["uid"] = user.id
    context.user_data["name"] = user.full_name

    kb = [
        [
            InlineKeyboardButton("✅ Approve", callback_data="approve"),
            InlineKeyboardButton("❌ Unapprove", callback_data="unapprove")
        ],
        [
            InlineKeyboardButton("♻ Reset Warn", callback_data="reset")
        ]
    ]

    update.message.reply_text(
        f"⚙ Admin Panel\n\n"
        f"👤 Name: {user.full_name}\n"
        f"🆔 ID: {user.id}",
        reply_markup=InlineKeyboardMarkup(kb)
    )

def buttons(update, context):
    q = update.callback_query
    q.answer()

    cid = q.message.chat.id
    uid = context.user_data.get("uid")
    name = context.user_data.get("name", "Unknown")

    if not uid:
        q.edit_message_text("Panel expired")
        return

    if q.data == "approve":
        bio_ok = 0 if has_link_in_bio(context, uid) else 1
        cur.execute(
            "INSERT OR REPLACE INTO approved VALUES (?,?,?)",
            (cid, uid, bio_ok)
        )
        db.commit()
        q.edit_message_text(
            f"✅ Approved\n👤 {name}\n🆔 {uid}\n"
            f"🔗 Bio clean: {'YES' if bio_ok else 'NO'}"
        )

    elif q.data == "unapprove":
        cur.execute(
            "DELETE FROM approved WHERE chat_id=? AND user_id=?",
            (cid, uid)
        )
        db.commit()
        q.edit_message_text(f"❌ Unapproved\n👤 {name}\n🆔 {uid}")

    elif q.data == "reset":
        reset_warn(cid, uid)
        q.edit_message_text(f"♻ Warn Reset\n👤 {name}\n🆔 {uid}")

# ================= MAIN HANDLER =================
def handler(update, context):
    msg = update.message
    cid = msg.chat.id
    uid = msg.from_user.id

    auto_unapprove_if_bio_link(context, cid, uid)

    if not is_approved(cid, uid) and has_link_in_bio(context, uid):
        try:
            msg.delete()
        except:
            pass
        context.bot.send_message(
            cid,
            f"⚠️ Message removed\n"
            f"👤 {safe_name(msg.from_user)}\n"
            f"🆔 {uid}\n"
            f"Remove link from bio then chat safely"
        )
        return

    if is_approved(cid, uid):
        return

    if (msg.text and contains_nsfw(msg.text)) or \
       (msg.caption and contains_nsfw(msg.caption)):
        punish(update, context)
        return

    if msg.photo:
        if is_porn_image(get_file_url(context.bot, msg.photo[-1].file_id)):
            punish(update, context)
        return

    if msg.video or msg.animation or msg.sticker or msg.contact:
        punish(update, context)

# ================= RUN =================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("panel", panel))
    dp.add_handler(CallbackQueryHandler(buttons))
    dp.add_handler(MessageHandler(Filters.all, handler))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
