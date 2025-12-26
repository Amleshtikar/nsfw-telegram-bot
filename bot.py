import os
import re
import asyncio
from datetime import timedelta

from telegram import Update, ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")

WARN_LIMIT = 3
MUTE_TIME = 10  # minutes

NSFW_WORDS = [
    "sex", "porn", "xxx", "nude", "boobs", "pussy",
    "dick", "fuck", "ass", "bhabhi", "hot girl"
]

NSFW_LINK_PATTERN = re.compile(
    r"(porn|xxx|xvideos|xnxx|redtube|onlyfans)",
    re.IGNORECASE
)

# ================= STORAGE =================
WARN_COUNT = {}        # user_id: count
APPROVED_USERS = set() # approved users bypass

# ================= HELPERS =================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )
    return member.status in (
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER
    )

async def punish_user(update, context, user):
    uid = user.id
    WARN_COUNT[uid] = WARN_COUNT.get(uid, 0) + 1

    if WARN_COUNT[uid] >= WARN_LIMIT:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=uid,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=timedelta(minutes=MUTE_TIME)
        )
        await update.effective_chat.send_message(
            f"🔇 {user.first_name} muted (3 warnings)"
        )
    else:
        await update.effective_chat.send_message(
            f"⚠️ Warning {WARN_COUNT[uid]}/{WARN_LIMIT} to {user.first_name}"
        )

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛡️ NSFW Guard Bot ONLINE")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = update.message.reply_to_message.from_user
    APPROVED_USERS.add(user.id)
    await update.message.reply_text(f"✅ Approved: {user.first_name}")

async def unapprove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = update.message.reply_to_message.from_user
    APPROVED_USERS.discard(user.id)
    await update.message.reply_text(f"❌ Unapproved: {user.first_name}")

async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = update.message.reply_to_message.from_user
    await punish_user(update, context, user)

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = update.message.reply_to_message.from_user
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        user.id,
        permissions=ChatPermissions(can_send_messages=False)
    )
    await update.message.reply_text(f"🔇 Muted {user.first_name}")

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = update.message.reply_to_message.from_user
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        user.id,
        permissions=ChatPermissions(can_send_messages=True)
    )
    await update.message.reply_text(f"🔊 Unmuted {user.first_name}")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    user = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(update.effective_chat.id, user.id)
    await update.message.reply_text(f"🚫 Banned {user.first_name}")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    uid = int(context.args[0])
    await context.bot.unban_chat_member(update.effective_chat.id, uid)
    await update.message.reply_text("♻️ User unbanned")

# ================= SCANNERS =================
async def scan_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in APPROVED_USERS:
        return

    text = update.message.text.lower()

    if any(w in text for w in NSFW_WORDS) or NSFW_LINK_PATTERN.search(text):
        await update.message.delete()
        await punish_user(update, context, user)

async def scan_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in APPROVED_USERS:
        return

    # sticker / gif / photo / video detected
    await update.message.delete()
    await punish_user(update, context, user)

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("warn", warn_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("unapprove", unapprove))

    # scanners
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, scan_text))
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.STICKER,
        scan_media
    ))

    print("NSFW Guard Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()            "MALE_GENITALIA_EXPOSED",
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
