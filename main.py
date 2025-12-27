import os
from flask import Flask, request
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Flask(__name__)

# ---------------- DATA ----------------
approved_users = set()
warns = {}

NSFW_KEYWORDS = [
    "porn", "sex", "xnxx", "xvideo", "xxx", "nude"
]

# ---------------- BOT ----------------
telegram_app = Application.builder().token(BOT_TOKEN).build()


# ---------- COMMANDS ----------
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in context.bot_data.get("admins", set()):
        if context.args:
            uid = int(context.args[0])
            approved_users.add(uid)
            await update.message.reply_text("✅ User approved")


async def unapprove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        uid = int(context.args[0])
        approved_users.discard(uid)
        await update.message.reply_text("❌ User unapproved")


# ---------- MESSAGE HANDLER ----------
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id

    # ignore admins
    if msg.from_user.is_bot:
        return

    # check NSFW
    text = (msg.text or "").lower()
    if any(word in text for word in NSFW_KEYWORDS):

        if user_id in approved_users:
            return

        # delete msg
        await msg.delete()

        # warn system
        warns[user_id] = warns.get(user_id, 0) + 1

        if warns[user_id] >= 3:
            await context.bot.restrict_chat_member(
                chat_id=msg.chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
            )
            await msg.chat.send_message(
                f"🔇 User muted (3 NSFW warnings)"
            )
        else:
            await msg.chat.send_message(
                f"⚠️ Warning {warns[user_id]}/3 : NSFW not allowed"
            )


# ---------- ADD HANDLERS ----------
telegram_app.add_handler(CommandHandler("approve", approve))
telegram_app.add_handler(CommandHandler("unapprove", unapprove))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))


# ---------- WEBHOOK ----------
@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    await telegram_app.process_update(update)
    return "ok"


# ---------- START ----------
if __name__ == "__main__":
    telegram_app.bot_data["admins"] = set()  # add admin IDs if needed
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
