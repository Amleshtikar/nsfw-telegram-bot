import os
from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WARN_LIMIT = 3

warns = {}
approved_users = set()

# ---------- HELPERS ----------

def is_admin(update: Update):
    member = update.effective_chat.get_member(update.effective_user.id)
    return member.status in ("administrator", "creator")

def get_uid(update: Update):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    return None

# ---------- START ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛡️ NSFW Guard Bot ONLINE")

# ---------- NSFW TEXT SCAN ----------

BAD_WORDS = [
    "sex", "porn", "xxx", "nude", "boobs", "fuck",
    "ass", "pussy", "dick", "bj", "handjob"
]

async def scan_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in approved_users:
        return

    text = (update.message.text or "").lower()

    if any(word in text for word in BAD_WORDS):
        await update.message.delete()
        await warn_user(update, context)

# ---------- WARN SYSTEM ----------

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    warns[uid] = warns.get(uid, 0) + 1

    if warns[uid] >= WARN_LIMIT:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=uid,
            permissions=ChatPermissions(can_send_messages=False),
        )
        await update.effective_chat.send_message(
            f"🔇 {user.mention_html()} muted (3 warnings)",
            parse_mode="HTML",
        )
    else:
        await update.effective_chat.send_message(
            f"⚠️ Warning {warns[uid]}/{WARN_LIMIT} to {user.mention_html()}",
            parse_mode="HTML",
        )

# ---------- ADMIN COMMANDS ----------

async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    uid = get_uid(update)
    if uid:
        warns[uid] = warns.get(uid, 0) + 1
        await update.message.reply_text("⚠️ Warn added")

async def unwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    uid = get_uid(update)
    if uid and uid in warns:
        warns[uid] -= 1
        await update.message.reply_text("♻️ Warn removed")

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    uid = get_uid(update)
    if uid:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            uid,
            ChatPermissions(can_send_messages=False),
        )
        await update.message.reply_text("🔇 User muted")

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    uid = get_uid(update)
    if uid:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            uid,
            ChatPermissions(can_send_messages=True),
        )
        await update.message.reply_text("🔊 User unmuted")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    uid = get_uid(update)
    if uid:
        await context.bot.ban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text("🚫 User banned")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    uid = get_uid(update)
    if uid:
        await context.bot.unban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text("♻️ User unbanned")

async def approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    uid = get_uid(update)
    if uid:
        approved_users.add(uid)
        await update.message.reply_text("🟢 User approved")

async def unapprove_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    uid = get_uid(update)
    if uid and uid in approved_users:
        approved_users.remove(uid)
        await update.message.reply_text("🔴 User unapproved")

# ---------- ADMIN PANEL ----------

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ Admin only")
        return

    keyboard = [
        [InlineKeyboardButton("⚠️ Warn", callback_data="warn"),
         InlineKeyboardButton("♻️ Unwarn", callback_data="unwarn")],
        [InlineKeyboardButton("🔇 Mute", callback_data="mute"),
         InlineKeyboardButton("🔊 Unmute", callback_data="unmute")],
        [InlineKeyboardButton("🚫 Ban", callback_data="ban"),
         InlineKeyboardButton("♻️ Unban", callback_data="unban")],
        [InlineKeyboardButton("🟢 Approve", callback_data="approve"),
         InlineKeyboardButton("🔴 Unapprove", callback_data="unapprove")],
    ]

    await update.message.reply_text(
        "🛡️ Admin Panel\n\nUser ke message par reply karke button dabao",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def panel_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    msg = query.message.reply_to_message
    if not msg:
        await query.message.reply_text("❗ User ke message par reply karo")
        return

    fake_update = Update(update.update_id, message=msg)

    actions = {
        "warn": warn_cmd,
        "unwarn": unwarn_cmd,
        "mute": mute_cmd,
        "unmute": unmute_cmd,
        "ban": ban_cmd,
        "unban": unban_cmd,
        "approve": approve_cmd,
        "unapprove": unapprove_cmd,
    }

    await actions[query.data](fake_update, context)

# ---------- MAIN ----------

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))

    app.add_handler(CommandHandler("warn", warn_cmd))
    app.add_handler(CommandHandler("unwarn", unwarn_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("approve", approve_cmd))
    app.add_handler(CommandHandler("unapprove", unapprove_cmd))

    app.add_handler(CallbackQueryHandler(panel_actions))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, scan_text))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    NSFW_LABELS = [
    "MALE_GENITALIA_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "ANUS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    ]

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

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, scan_text))

    print("Bot started...")
    app.run_polling()
