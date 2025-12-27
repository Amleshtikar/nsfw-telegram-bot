import os
from flask import Flask, request
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from datetime import timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN")

NSFW_KEYWORDS = [
    "sex", "girl", "boy", "vip", "service",
    "hot", "call", "paid", "dating", "escort"
]

warns = {}
approved_users = set()

app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

# ---------------- ADMIN CHECK ----------------
async def is_admin(update: Update):
    member = await update.effective_chat.get_member(update.effective_user.id)
    return member.status in ("administrator", "creator")

# ---------------- CONTACT HANDLER ----------------
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.contact:
        return

    uid = msg.from_user.id
    chat_id = msg.chat.id

    if uid in approved_users:
        return

    name = ((msg.contact.first_name or "") + (msg.contact.last_name or "")).lower()

    if not any(k in name for k in NSFW_KEYWORDS):
        return  # normal contact ignore

    await msg.delete()

    warns[uid] = warns.get(uid, 0) + 1
    count = warns[uid]

    if count <= 2:
        await context.bot.send_message(
            chat_id,
            f"⚠ Warning {count}/2\nNSFW contact not allowed"
        )

    elif count == 3:
        await context.bot.restrict_chat_member(
            chat_id,
            uid,
            ChatPermissions(can_send_messages=False),
            until_date=timedelta(minutes=10)
        )
        await context.bot.send_message(
            chat_id,
            "🔇 User muted for 10 minutes (NSFW contact)"
        )

# ---------------- ADMIN COMMANDS ----------------
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    if not update.message.reply_to_message:
        return
    approved_users.add(update.message.reply_to_message.from_user.id)
    await update.message.reply_text("✅ User approved")

async def unapprove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update):
        return
    if not update.message.reply_to_message:
        return
    approved_users.discard(update.message.reply_to_message.from_user.id)
    await update.message.reply_text("❌ User unapproved")

# ---------------- HANDLERS ----------------
application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
application.add_handler(CommandHandler("approve", approve))
application.add_handler(CommandHandler("unapprove", unapprove))

# ---------------- WEBHOOK ----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.json, application.bot)
    application.create_task(application.process_update(update))
    return "ok"

@app.route("/")
def home():
    return "Bot running"
