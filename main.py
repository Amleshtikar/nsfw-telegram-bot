import os
from telegram import Update, ChatPermissions
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ===== DATA =====
approved_users = set()
warns = {}

# ===== HELPERS =====
def is_admin(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    admins = context.bot.get_chat_administrators(chat_id)
    return user_id in [a.user.id for a in admins]

def is_nsfw_contact(message):
    if not message.contact:
        return False
    name = (message.contact.first_name or "").lower()
    nsfw_words = ["sex", "porn", "xxx", "adult"]
    return any(w in name for w in nsfw_words)

# ===== COMMANDS =====
def start(update: Update, context: CallbackContext):
    update.message.reply_text("NSFW Contact Delete Bot Active ✅")

def approve(update: Update, context: CallbackContext):
    if not is_admin(update, context):
        return
    user_id = update.message.reply_to_message.from_user.id
    approved_users.add(user_id)
    update.message.reply_text("User approved ✅")

def unapprove(update: Update, context: CallbackContext):
    if not is_admin(update, context):
        return
    user_id = update.message.reply_to_message.from_user.id
    approved_users.discard(user_id)
    update.message.reply_text("User unapproved ❌")

def stats(update: Update, context: CallbackContext):
    update.message.reply_text(f"Warned users: {len(warns)}")

# ===== MESSAGE HANDLER =====
def handle_message(update: Update, context: CallbackContext):
    msg = update.message
    user_id = msg.from_user.id
    chat_id = msg.chat_id

    if user_id in approved_users:
        return

    if is_nsfw_contact(msg):
        msg.delete()

        warns[user_id] = warns.get(user_id, 0) + 1
        count = warns[user_id]

        if count < 3:
            context.bot.send_message(
                chat_id,
                f"⚠️ Warning {count}/2\nNSFW contact not allowed!"
            )
        else:
            context.bot.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions(can_send_messages=False),
            )
            context.bot.send_message(
                chat_id,
                "🔇 You are muted (NSFW contact spam)"
            )

# ===== MAIN =====
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("approve", approve))
    dp.add_handler(CommandHandler("unapprove", unapprove))
    dp.add_handler(CommandHandler("stats", stats))

    dp.add_handler(MessageHandler(Filters.contact, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
