import os
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Porn keywords
BAD_WORDS = [
    "porn", "sex", "xxx", "nude", "fuck",
    "chut", "lund", "boobs", "pussy",
]

async def anti_porn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    # Check text / caption
    text = (msg.text or msg.caption or "").lower()
    if any(word in text for word in BAD_WORDS):
        await msg.delete()
        return

    # Delete stickers
    if msg.sticker:
        if msg.sticker.is_animated or msg.sticker.is_video:
            await msg.delete()
            return

    # Delete GIFs
    if msg.animation:
        await msg.delete()
        return

    # Delete videos
    if msg.video:
        await msg.delete()
        return

    # Delete photos with caption
    if msg.photo and msg.caption:
        await msg.delete()
        return

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.ALL & filters.ChatType.GROUPS,
            anti_porn
        )
    )

    app.run_polling()

if __name__ == "__main__":
    main()
