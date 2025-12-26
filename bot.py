import os
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is running")

# ---------- TEST REPLY ----------
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Reply aa raha hai")

# ---------- MAIN ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, test))

    print("Bot started successfully")
    app.run_polling()

if __name__ == "__main__":
    main()
