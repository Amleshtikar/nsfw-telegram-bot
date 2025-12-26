import os
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("BOT ALIVE ✅")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, test))
    app.run_polling()

if __name__ == "__main__":
    main()
