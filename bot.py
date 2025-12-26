import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Environment Variables (Railway Dashboard mein set karein)
TOKEN = os.getenv("BOT_TOKEN")
SIGHTENGINE_USER = os.getenv("SIGHTENGINE_USER")
SIGHTENGINE_SECRET = os.getenv("SIGHTENGINE_SECRET")

# Warnings track karne ke liye dictionary
user_warnings = {}

async def check_nsfw(image_url):
    """Sightengine API se image check karne ka function"""
    params = {
        'models': 'nudity-2.0',
        'api_user': SIGHTENGINE_USER,
        'api_secret': SIGHTENGINE_SECRET,
        'url': image_url
    }
    try:
        r = requests.get('https://api.sightengine.com/1.0/check.json', params=params)
        output = r.json()
        if output['status'] == 'success':
            # Agar 'sexual' score 0.5 se zyada hai toh NSFW mana jayega
            nudity = output['nudity']
            if nudity.get('sexual_display', 0) > 0.5 or nudity.get('erotica', 0) > 0.5:
                return True
        return False
    except Exception as e:
        logging.error(f"Detection Error: {e}")
        return False

async def handle_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    msg = update.message
    user = update.effective_user
    chat_id = update.effective_chat.id

    # Media detect karna
    is_media = msg.photo or msg.sticker or msg.animation or msg.video
    
    if is_media:
        # File ka link nikalna (Detection ke liye)
        if msg.photo:
            file = await msg.photo[-1].get_file()
        elif msg.animation:
            file = await msg.animation.get_file()
        elif msg.sticker:
            file = await msg.sticker.get_file()
        else:
            return # Videos ka check complex hota hai, abhi skip kar rahe hain

        file_url = file.file_path

        # AI se check karwana
        if await check_nsfw(file_url):
            # Message delete karein
            await msg.delete()

            # Warning system
            user_id = user.id
            user_warnings[user_id] = user_warnings.get(user_id, 0) + 1
            count = user_warnings[user_id]

            if count >= 3:
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.send_message(chat_id, f"❌ {user.first_name} ko 3 warnings ke baad Ban kar diya gaya.")
                user_warnings[user_id] = 0
            else:
                await context.bot.send_message(
                    chat_id, 
                    f"⚠️ {user.mention_html()} NSFW content allow nahi hai! Warning: {count}/3",
                    parse_mode='HTML'
                )

def main():
    if not TOKEN:
        print("Error: BOT_TOKEN nahi mila!")
        return
        
    application = Application.builder().token(TOKEN).build()
    
    # Sabhi media files ke liye handler
    media_filter = (filters.PHOTO | filters.Sticker.ALL | filters.ANIMATION)
    application.add_handler(MessageHandler(media_filter, handle_content))

    print("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
