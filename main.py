import os
import re
from telegram import Update, ChatPermissions
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

approved_users = set()
warns = {}

NSFW_WORDS = [
    "sex", "porn", "xxx", "adult", "nude", "fuck",
    "chut", "lund", "boobs", "pussy", "randi"
]

# ---------- HELPERS ----------

def is_admin(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    admins = context.bot.get_chat_administrators(chat_id)
    return user_id in [a.user.id for a in admins]

def contains_nsfw(text: str):
    if not text:
        return False
    text = text.lower()
    return any(w in text for w in NSFW_WORDS)

def is_nsfw_message(msg):
    # TEXT
    if msg.text and contains_nsfw(msg.text):
        return True

    # CAPTION (photo/video/gif)
    if msg.caption and contains_nsfw(msg.caption):
        return True

    # STICKER
    if msg.sticker:
        emoji = msg.sticker.emoji or ""
        return contains_nsfw(emoji)

    # CONTACT
    if msg.contact:
        name = (
            (msg.contact.first_name or "") +
            (msg.contact.last_name or "")
        ).lower()
        phone = msg.contact.phone_number or ""
        return contains_nsfw(name) or len(phone) >= 10

    return False

def warn_and_action(update, context):
    msg = update.message
    user_id = msg.from_user.id
    chat_id = msg.chat_id

    msg.delete()

    warns[user_id] = warns.get(user_id, 0) + 1
    count = warns[user_id]

    if count < 3:
        context.bot.send_message(
            chat_id,
            f"⚠️ Warning {count}/2\nNSFW content not allowed"
        )
    else:
        context.bot.restrict_chat_member(
            chat_id,
            user_id,
            ChatPermissions(can_send_messages=False)
        )
        context.bot.send_message(
            chat_id,
            "🔇 You are muted for NSFW spam"
        )

# ---------- COMMANDS ----------

def start(update: Update, context: CallbackContext):
    update.message.reply_text("🛡 NSFW Admin Bot Active")

def approve(update: Update, context: CallbackContext):
    if not is_admin(update, context):
        return
    if not update.message.reply_to_message:
        return
    uid = update.message.reply_to_message.from_user.id
    approved_users.add(uid)
    update.message.reply_text("✅ User approved")

def unapprove(update: Update, context: CallbackContext):
    if not is_admin(update, context):
        return
    if not update.message.reply_to_message:
        return
    uid = update.message.reply_to_message.from_user.id
    approved_users.discard(uid)
    update.message.reply_text("❌ User unapproved")

def warns_cmd(update: Update, context: CallbackContext):
    update.message.reply_text(f"⚠️ Warned users: {len(warns)}")

def resetwarn(update: Update, context: CallbackContext):
    if not is_admin(update, context):
        return
    if not update.message.reply_to_message:
        return
    uid = update.message.reply_to_message.from_user.id
    warns.pop(uid, None)
    update.message.reply_text("♻️ Warn reset")

# ---------- MESSAGE HANDLER ----------

def handle_all(update: Update, context: CallbackContext):
    msg = update.message
    user_id = msg.from_user.id

    if user_id in approved_users:
        return

    if is_nsfw_message(msg):
        warn_and_action(update, context)

# ---------- MAIN ----------

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("approve", approve))
    dp.add_handler(CommandHandler("unapprove", unapprove))
    dp.add_handler(CommandHandler("warns", warns_cmd))
    dp.add_handler(CommandHandler("resetwarn", resetwarn))

    dp.add_handler(MessageHandler(Filters.all, handle_all))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
