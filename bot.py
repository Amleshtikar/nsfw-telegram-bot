import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

# Logging
logging.basicConfig(level=logging.INFO)

# Config (Railway Variables se aayenge)
TOKEN = os.getenv("BOT_TOKEN")
SIGHTENGINE_USER = os.getenv("SIGHTENGINE_USER")
SIGHTENGINE_SECRET = os.getenv("SIGHTENGINE_SECRET")
ADMIN_ID = int(os.getenv("ADMIN_ID")) # Aapki apni ID

# Data (In-memory, restart par reset hoga. Permanent ke liye DB chahiye)
approved_files = set() # Approved file_ids
user_stats = {} # {user_id: {'warns': 0}}

# --- NSFW Detection Function ---
async def is_porn(file_url):
    params = {
        'models': 'nudity-2.0',
        'api_user': SIGHTENGINE_USER,
        'api_secret': SIGHTENGINE_SECRET,
        'url': file_url
    }
    r = requests.get('https://api.sightengine.com/1.0/check.json', params=params)
    output = r.json()
    if output.get('status') == 'success':
        nudity = output['nudity']
        # Agar nudity score high hai
        if nudity.get('sexual_display', 0) > 0.5 or nudity.get('erotica', 0) > 0.5:
            return True
    return False

# --- Admin Commands ---
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if update.message.reply_to_message:
        reply = update.message.reply_to_message
        file_id = None
        if reply.photo: file_id = reply.photo[-1].file_id
        elif reply.sticker: file_id = reply.sticker.file_id
        
        if file_id:
            approved_files.add(file_id)
            await update.message.reply_text("✅ Ye media approve kar diya gaya hai.")

# --- Main Logic ---
async def filter_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Check if message has media
    media = msg.photo or msg.sticker or msg.animation or msg.video
    if not media: return

    # 1. Check if already approved
    file_id = None
    if msg.photo: file_id = msg.photo[-1].file_id
    elif msg.sticker: file_id = msg.sticker.file_id
    elif msg.animation: file_id = msg.animation.file_id
    
    if file_id in approved_files:
        return # Ignore approved content

    # 2. Get File URL and Scan
    file = await context.bot.get_file(file_id)
    if await is_porn(file.file_path):
        # 3. Action Logic
        await msg.delete()
        user_id = user.id
        if user_id not in user_stats: user_stats[user_id] = 0
        
        user_stats[user_id] += 1
        count = user_stats[user_id]

        if count == 1 or count == 2:
            await context.bot.send_message(chat_id, f"⚠️ Warning {count}/2: {user.first_name}, Porn content allow nahi hai!")
        elif count == 3:
            # Mute logic (Permissions remove karna)
            from datetime import timedelta
            await context.bot.restrict_chat_member(chat_id, user_id, permissions={'can_send_messages': False}, until_date=timedelta(hours=24))
            await context.bot.send_message(chat_id, f"🔇 {user.first_name} ko 3 warnings ke baad 24 ghante ke liye MUTE kar diya gaya.")
            user_stats[user_id] = 0 # Reset after mute

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Sticker.ALL | filters.ANIMATION, filter_media))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
