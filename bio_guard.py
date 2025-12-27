# bio_guard.py
import sqlite3

BIO_KEYS = ["http","https","t.me","telegram.me",".com",".in","@"]

db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS approved (
    chat_id INTEGER,
    user_id INTEGER,
    bio_ok INTEGER,
    PRIMARY KEY (chat_id, user_id)
)
""")
db.commit()

# ---------------- HELPERS ----------------
def has_bio_link(ctx, uid):
    try:
        bio = (ctx.bot.get_chat(uid).bio or "").lower()
        return any(k in bio for k in BIO_KEYS)
    except:
        return False

def is_approved(chat_id, user_id):
    cur.execute(
        "SELECT bio_ok FROM approved WHERE chat_id=? AND user_id=?",
        (chat_id, user_id)
    )
    return cur.fetchone()

def auto_unapprove(ctx, chat_id, user_id):
    row = is_approved(chat_id, user_id)
    if row and row[0] == 1 and has_bio_link(ctx, user_id):
        cur.execute(
            "DELETE FROM approved WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )
        db.commit()

# ---------------- COMMANDS ----------------
def approve_cmd(update, ctx):
    if not update.message.reply_to_message:
        return
    u = update.message.reply_to_message.from_user
    bio_ok = 0 if has_bio_link(ctx, u.id) else 1
    cur.execute(
        "INSERT OR REPLACE INTO approved VALUES (?,?,?)",
        (update.message.chat.id, u.id, bio_ok)
    )
    db.commit()
    update.message.reply_text(f"✅ Approved\n👤 {u.full_name}")

def unapprove_cmd(update, ctx):
    if not update.message.reply_to_message:
        return
    u = update.message.reply_to_message.from_user
    cur.execute(
        "DELETE FROM approved WHERE chat_id=? AND user_id=?",
        (update.message.chat.id, u.id)
    )
    db.commit()
    update.message.reply_text(f"❌ Unapproved\n👤 {u.full_name}")

# ---------------- MAIN CHECK ----------------
def bio_guard(update, ctx):
    m = update.message
    cid = m.chat.id
    uid = m.from_user.id

    auto_unapprove(ctx, cid, uid)

    # approved user → ignore everything
    if is_approved(cid, uid):
        return True

    # bio link detected → delete ALL messages (no warn)
    if has_bio_link(ctx, uid):
        try:
            m.delete()
        except:
            pass

        ctx.bot.send_message(
            cid,
            f"⚠️ {m.from_user.full_name}\n"
            "❌ Aapki bio me link hai\n"
            "👉 Pehle bio se link hatao\n"
            "✅ Phir message bhejo"
        )
        return True

    return False
