import os, sqlite3, requests
from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
SE_USER = os.getenv("SE_USER")
SE_SECRET = os.getenv("SE_SECRET")

MUTE_TIME = 300

NSFW_WORDS = [
    "sex","porn","xxx","nude","adult",
    "fuck","chut","lund","boobs","pussy","randi"
]

PORN_EMOJIS = ["🍆","🍑","💦","🔥","🥵","😈","🍒"]

# ================= DATABASE =================
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS warns (chat_id INTEGER,user_id INTEGER,count INTEGER,PRIMARY KEY(chat_id,user_id))")
db.commit()

# ================= HELPERS =================
def safe_name(u): 
    return u.full_name.replace("<","").replace(">","")

def is_admin(ctx,cid,uid):
    return uid in [a.user.id for a in ctx.bot.get_chat_administrators(cid)]

def contains_nsfw(text):
    if not text: return False
    t=text.lower()
    return any(w in t for w in NSFW_WORDS)

def get_file_url(bot,fid):
    f=bot.get_file(fid)
    return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f.file_path}"

def is_porn_image(url):
    try:
        r=requests.post(
            "https://api.sightengine.com/1.0/check.json",
            params={"models":"nudity-2.1","api_user":SE_USER,"api_secret":SE_SECRET},
            files={"media":requests.get(url,timeout=10).content},
            timeout=15
        )
        n=r.json().get("nudity",{})
        return n.get("sexual_activity",0)+n.get("sexual_display",0)>=0.6
    except:
        return False

# ================= ADVANCED SCAN =================
def is_porn_sticker(msg):
    # emoji logic
    if msg.sticker.emoji and msg.sticker.emoji in PORN_EMOJIS:
        return True

    # sticker set name logic
    if msg.sticker.set_name and contains_nsfw(msg.sticker.set_name.lower()):
        return True

    # animated/video sticker → suspicious
    if msg.sticker.is_animated or msg.sticker.is_video:
        return True

    return False

def is_porn_gif(msg):
    # text / emoji check
    if contains_nsfw(msg.caption or ""):
        return True

    # size + duration heuristic
    if msg.animation.file_size and msg.animation.file_size > 400000:
        return True

    return False

# ================= WARN / MUTE =================
def add_warn(cid,uid):
    cur.execute("SELECT count FROM warns WHERE chat_id=? AND user_id=?",(cid,uid))
    r=cur.fetchone()
    if r:
        cur.execute("UPDATE warns SET count=count+1 WHERE chat_id=? AND user_id=?",(cid,uid))
        db.commit(); return r[0]+1
    cur.execute("INSERT INTO warns VALUES (?,?,1)",(cid,uid))
    db.commit(); return 1

def reset_warn(cid,uid):
    cur.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?",(cid,uid))
    db.commit()

def punish(update,ctx):
    m=update.message; cid=m.chat.id; uid=m.from_user.id
    try: m.delete()
    except: pass
    c=add_warn(cid,uid)
    if c<3:
        ctx.bot.send_message(cid,f"⚠️ Warning {c}/2\n👤 {safe_name(m.from_user)}\n🆔 {uid}")
    else:
        ctx.bot.restrict_chat_member(cid,uid,ChatPermissions(can_send_messages=False))
        kb=InlineKeyboardMarkup([[InlineKeyboardButton("🔊 Unmute",callback_data=f"unmute:{uid}")]])
        ctx.bot.send_message(cid,f"🔇 Muted 5 min\n👤 {safe_name(m.from_user)}\n🆔 {uid}",reply_markup=kb)
        ctx.job_queue.run_once(unmute_job,MUTE_TIME,context={"chat_id":cid,"user_id":uid})

def unmute_job(ctx):
    d=ctx.job.context
    ctx.bot.restrict_chat_member(d["chat_id"],d["user_id"],ChatPermissions(can_send_messages=True))
    reset_warn(d["chat_id"],d["user_id"])

def buttons(update,ctx):
    q=update.callback_query; cid=q.message.chat.id; q.answer()
    if not is_admin(ctx,cid,q.from_user.id):
        q.answer("Only admin",show_alert=True); return
    uid=int(q.data.split(":")[1])
    ctx.bot.restrict_chat_member(cid,uid,ChatPermissions(can_send_messages=True))
    reset_warn(cid,uid)
    q.edit_message_text("✅ User Unmuted")

# ================= MAIN HANDLER =================
def handler(update,ctx):
    m=update.message

    if m.text or m.caption:
        if contains_nsfw(m.text or m.caption):
            punish(update,ctx); return

    if m.photo:
        if is_porn_image(get_file_url(ctx.bot,m.photo[-1].file_id)):
            punish(update,ctx); return

    if m.sticker:
        if is_porn_sticker(m):
            punish(update,ctx); return

    if m.animation:
        if is_porn_gif(m):
            punish(update,ctx); return

# ================= RUN =================
def main():
    up=Updater(BOT_TOKEN,use_context=True)
    dp=up.dispatcher
    dp.add_handler(CommandHandler("start",lambda u,c:u.message.reply_text("🛡 AI + Human Protection Active")))
    dp.add_handler(CallbackQueryHandler(buttons))
    dp.add_handler(MessageHandler(Filters.all,handler))
    up.start_polling(); up.idle()

if __name__=="__main__":
    main()
