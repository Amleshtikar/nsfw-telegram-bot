from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, MessageHandler,
    CommandHandler, ContextTypes, filters
)
from nudenet import NudeDetector
from PIL import Image
import cv2, datetime
from config import BOT_TOKEN, WARN_LIMIT

detector = NudeDetector()

approved_users = set()
warns = {}
SCAN_ENABLED = True

# ---------- SCAN FUNCTIONS ----------

def scan_text(text):
    words = ["sex","porn","xxx","nude","xnxx","xvideos","chut","lund"]
    text = text.lower()
    return any(w in text for w in words)

def scan_links(text):
    sites = ["pornhub","xnxx","xvideos","redtube"]
    return any(s in text.lower() for s in sites)

def scan_image(path):
    img = Image.open(path)
    img.thumbnail((640, 640))
    img.save(path)

    result = detector.detect(path)
    for r in result:
        if r["class"] in [
            "FEMALE_GENITALIA_EXPOSED",
            "MALE_GENITALIA_EXPOSED",
            "FEMALE_BREAST_EXPOSED"
        ]:
            return True
    return False

def scan_video(path):
    cap = cv2.VideoCapture(path)
    ok, frame = cap.read()
    if ok:
        cv2.imwrite("frame.jpg", frame)
        return scan_image("frame.jpg")
    return False

# ---------- WARN SYSTEM ----------

async def warn_user(user_id, update, context):
    warns[user_id] = warns.get(user_id, 0) + 1
    if warns[user_id] >= WARN_LIMIT:
        until = datetime.datetime.now() + datetime.timedelta(minutes=10)
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            user_id,
            ChatPermissions(can_send_messages=False),
            until_date=until
        )
        await update.message.reply_text("🚫 Muted (3 warnings)")
    else:
        await update.message.reply_text(
            f"⚠️ Warning {warns[user_id]}/{WARN_LIMIT}"
        )

# ---------- MAIN SCAN ----------

async def full_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not SCAN_ENABLED:
        return

    msg = update.message
    user = update.effective_user

    if user.id in approved_users:
        return

    nsfw = False

    text = msg.text or msg.caption
    if text and (scan_text(text) or scan_links(text)):
        nsfw = True

    if msg.photo:
        f = await msg.photo[-1].get_file()
        await f.download_to_drive("img.jpg")
        nsfw = scan_image("img.jpg")

    if msg.sticker:
        f = await msg.sticker.get_file()
        await f.download_to_drive("stk.png")
        nsfw = scan_image("stk.png")

    if msg.animation:
        f = await msg.animation.get_file()
        await f.download_to_drive("gif.mp4")
        nsfw = scan_video("gif.mp4")

    if msg.video:
        f = await msg.video.get_file()
        await f.download_to_drive("vid.mp4")
        nsfw = scan_video("vid.mp4")

    if nsfw:
        await msg.delete()
        await warn_user(user.id, update, context)

# ---------- ADMIN COMMANDS ----------

async def approve(update, context):
    uid = int(context.args[0])
    approved_users.add(uid)
    await update.message.reply_text("✅ Approved")

async def unapprove(update, context):
    uid = int(context.args[0])
    approved_users.discard(uid)
    await update.message.reply_text("❌ Unapproved")

async def scan_on(update, context):
    global SCAN_ENABLED
    SCAN_ENABLED = True
    await update.message.reply_text("✅ Scan ON")

async def scan_off(update, context):
    global SCAN_ENABLED
    SCAN_ENABLED = False
    await update.message.reply_text("❌ Scan OFF")

# ---------- START BOT ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(MessageHandler(filters.ALL, full_scan))
app.add_handler(CommandHandler("approve", approve))
app.add_handler(CommandHandler("unapprove", unapprove))
app.add_handler(CommandHandler("scan_on", scan_on))
app.add_handler(CommandHandler("scan_off", scan_off))

app.run_polling()
