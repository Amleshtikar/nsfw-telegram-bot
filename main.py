import os
from flask import Flask, request
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
from datetime import timedelta

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")

NSFW_KEYWORDS = [
    "sex", "girl", "boy", "vip", "service", "hot",
    "call", "paid", "dating", "escort"
]

# ================= MEMORY =================
warns = {}              # user_id: warn_count
approved_users = set()  # approved user ids

# ================= APP ====================
app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

# ================= HELPERS =================
def is_admin(update: Update):
    user = update.effective_user
    chat = update.effective_chat
    member = chat.get_member(user.id)
    return member.status in ("administrator", "creator")

# ================= CORE LOGIC =================
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.contact:
        return

    chat_id = msg.chat.id
    user = msg.from_user
    uid = user.id

    # Approved user → ignore
    if uid in approved_users:
        return

    # Contact name check
    name = (
        (msg.contact.first_name or "") +
        (msg.contact.last_name or "")
    ).lower()

    # Normal contact → ignore
    if not any(k in name for k in NSFW_KEYWORDS):
        return

    # NSFW contact detected
    await msg.delete()

    warns[uid] = warns.get(uid, 0) + 1
    count = warns[uid]

    if count <= 2:
        await context.bot.send_message(
            chat_id,
            f"⚠ Warning {count}/2\n"
            f"NSFW contact allowed nahi hai.\n"
            f"User: {user.mention_html()}",
            parse_mode="HTML"
        )

    elif count == 3:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=uid,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=timedelta(minutes=10)
        )
        await context.bot.send_message(
            chat_id,
            f"🔇 User muted for 10 minutes\n"
            f"Reason: NSFW contact\n"
            f"User: {user.mention_html()}",
            parse_mode="HTML"
        )

# ================= ADMIN COMMANDS =================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not update.message.reply_to_message:
        return

    uid = update.message.reply_to_message.from_user.id
    approved_users.add(uid)
    await update.message.reply_text("✅ User approved")

async def unapprove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not update.message.reply_to_message:
        return

    uid = update.message.reply_to_message.from_user.id
    approved_users.discard(uid)
    await update.message.reply_text("❌ User unapproved")

async def warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not update.message.reply_to_message:
        return

    uid = update.message.reply_to_message.from_user.id
    count = warns.get(uid, 0)
    await update.message.reply_text(f"⚠ Warnings: {count}")

async def resetwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    if not update.message.reply_to_message:
        return

    uid = update.message.reply_to_message.from_user.id
    warns.pop(uid, None)
    await update.message.reply_text("♻ Warnings reset")

# ================= HANDLERS =================
application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
application.add_handler(CommandHandler("approve", approve))
application.add_handler(CommandHandler("unapprove", unapprove))
application.add_handler(CommandHandler("warns", warns_cmd))
application.add_handler(CommandHandler("resetwarn", resetwarn))

# ================= WEBHOOK =================
@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.json, application.bot)
    await application.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "NSFW Contact Bot Running"
