import logging
import asyncio
import json
import os
import threading
import time
import requests
import html
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler, Application
from telegram.request import HTTPXRequest

# ================= CONFIGURATION =================
BOT_TOKEN = "8486877952:AAHa-oYkSXuwYUQza6wSc6Vx9WtSOP5tiNI"
CHANNEL_LINK = "@KAMOD_CODEX"
OWNER_LINK = "@kamod90"
ADMIN_ID = 8138834246
GROUP_LINK = "@KAMOD_LIKE_GROUP"
MUST_JOIN_CHANNELS = ["@KAMOD_CODEX"]

DATA_FILE = "users.json"
AUTOLIKE_RUN_HOUR = 4  # 4:00 AM IST

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ==============================================================================
#             SAFE DATABASE SYSTEM
# ==============================================================================
MEM_DATA = {
    "cooldowns": {},
    "premium": {},
    "all_users": [],
    "maintenance": False,
    "usernames": {},
    "autolike": [],
    "admins": {},
    "like_history": {},
    "daily_summary": {}
}
DATA_LOCK = threading.Lock()

def load_data_initial():
    global MEM_DATA
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        print("⚠️ Users file missing or empty. Creating new database.")
        save_data_force()
        return
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data.get("premium"), list):
                new_prem = {}
                expiry = (datetime.now() + timedelta(days=30)).isoformat()
                for uid in data["premium"]:
                    new_prem[str(uid)] = expiry
                data["premium"] = new_prem
            for key in MEM_DATA:
                if key in data:
                    MEM_DATA[key] = data[key]
            print(f"✅ Database Loaded: {len(MEM_DATA['all_users'])} Users")
    except json.JSONDecodeError:
        print("❌ Database Corrupted! Backup created.")
        os.rename(DATA_FILE, "users_backup.json")
        save_data_force()
    except Exception as e:
        print(f"DB Error: {e}")

def save_data_force():
    with DATA_LOCK:
        temp_file = f"{DATA_FILE}.tmp"
        try:
            with open(temp_file, "w") as f:
                json.dump(MEM_DATA, f, indent=4)
            os.replace(temp_file, DATA_FILE)
        except Exception as e:
            print(f"❌ Save Failed: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

def background_db_saver():
    while True:
        time.sleep(30)
        try:
            save_data_force()
        except:
            pass

def record_user(user):
    uid = user.id
    username = user.username.lower() if user.username else None
    with DATA_LOCK:
        if uid not in MEM_DATA["all_users"]:
            MEM_DATA["all_users"].append(uid)
        if username:
            MEM_DATA["usernames"][username] = uid

def get_data():
    return MEM_DATA

def get_india_time():
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

def fmt_num(n):
    try:
        return f"{int(n):,}"
    except:
        return str(n)

# ==============================================================================
#             PREMIUM POSTER BUILDERS (ALL BOLD + EMOJI)
# ==============================================================================
def build_like_success(player_name, uid, region, before, added, after):
    return (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  ✅ 𝐋𝐈𝐊𝐄 𝐒𝐄𝐍𝐓 𝐒𝐔𝐂𝐂𝐄𝐒𝐒𝐅𝐔𝐋𝐋𝐘 ✅\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 👤 𝐏𝐋𝐀𝐘𝐄𝐑 𝐈𝐍𝐅𝐎 ✦ ⟯\n"
        f"│  👑 𝐍𝐚𝐦𝐞   : <b>{html.escape(player_name)}</b>\n"
        f"│  🆔 𝐔𝐈𝐃    : <code>{html.escape(str(uid))}</code> 🧩\n"
        f"│  🌍 𝐑𝐞𝐠𝐢𝐨𝐧 : <b>{html.escape(str(region).upper())}</b> 🧩\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ ❤️ 𝐋𝐈𝐊𝐄 𝐃𝐄𝐓𝐀𝐈𝐋𝐒 ✦ ⟯\n"
        f"│  📉 𝐁𝐞𝐟𝐨𝐫𝐞 : <b>{fmt_num(before)}</b> ❄️\n"
        f"│  ❤️ 𝐆𝐢𝐯𝐞𝐧  : <b>{fmt_num(added)}</b> 🧩\n"
        f"│  📈 𝐀𝐟𝐭𝐞𝐫  : <b>{fmt_num(after)}</b> 🍁\n"
        "╰━━━━━━━━━━━━━━━━━━✪"
    )

def build_like_fail(player_name, uid, region, before, added, after, reason=""):
    txt = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  ❌ 𝐋𝐈𝐊𝐄 𝐃𝐄𝐋𝐈𝐕𝐄𝐑𝐘 𝐅𝐀𝐈𝐋𝐄𝐃 ❌\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 👤 𝐏𝐋𝐀𝐘𝐄𝐑 𝐈𝐍𝐅𝐎 ✦ ⟯\n"
        f"│  👑 𝐍𝐚𝐦𝐞   : <b>{html.escape(player_name)}</b>\n"
        f"│  🆔 𝐔𝐈𝐃    : <code>{html.escape(str(uid))}</code> 🧩\n"
        f"│  🌍 𝐑𝐞𝐠𝐢𝐨𝐧 : <b>{html.escape(str(region).upper())}</b> 🧩\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ ❤️ 𝐋𝐈𝐊𝐄 𝐃𝐄𝐓𝐀𝐈𝐋𝐒 ✦ ⟯\n"
        f"│  📉 𝐁𝐞𝐟𝐨𝐫𝐞 : <b>{fmt_num(before)}</b> ❄️\n"
        f"│  📈 𝐀𝐟𝐭𝐞𝐫  : <b>{fmt_num(after)}</b> 🍁\n"
        f"│  ❤️ 𝐀𝐝𝐝𝐞𝐝  : <b>+{fmt_num(added)}</b> 🧩\n"
        "╰━━━━━━━━━━━━━━━━━━✪"
    )
    if reason:
        txt += f"\n\n⚠️ 𝐀𝐏𝐈 : <b>{html.escape(reason[:250])}</b>"
    return txt

def build_auto_like(player_name, uid, region, before, added, after,
                    plan_label, remaining_days=None, status_ok=True):
    head = (
        "✅ 𝐀𝐔𝐓𝐎 𝐋𝐈𝐊𝐄 𝐒𝐔𝐂𝐂𝐄𝐒𝐒 ✅"
        if status_ok else
        "❌ 𝐀𝐔𝐓𝐎 𝐋𝐈𝐊𝐄 𝐅𝐀𝐈𝐋𝐄𝐃 ❌"
    )
    txt = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        f"│  {head}\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 👤 𝐏𝐋𝐀𝐘𝐄𝐑 𝐈𝐍𝐅𝐎 ✦ ⟯\n"
        f"│  👑 𝐍𝐚𝐦𝐞   : <b>{html.escape(player_name)}</b>\n"
        f"│  🎯 𝐓𝐚𝐫𝐠𝐞𝐭 : <code>{html.escape(str(uid))}</code> 🧩\n"
        f"│  🌍 𝐑𝐞𝐠𝐢𝐨𝐧 : <b>{html.escape(str(region).upper())}</b> 🧩\n"
        f"│  💠 𝐏𝐥𝐚𝐧   : <b>{plan_label}</b>\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ ❤️ 𝐋𝐈𝐊𝐄 𝐃𝐄𝐓𝐀𝐈𝐋𝐒 ✦ ⟯\n"
        f"│  📉 𝐁𝐞𝐟𝐨𝐫𝐞 : <b>{fmt_num(before)}</b> ❄️\n"
        f"│  ❤️ 𝐆𝐢𝐯𝐞𝐧  : <b>{fmt_num(added)}</b> 🧩\n"
        f"│  📈 𝐀𝐟𝐭𝐞𝐫  : <b>{fmt_num(after)}</b> 🍁\n"
        "╰━━━━━━━━━━━━━━━━━━✪"
    )
    if remaining_days is not None:
        txt += f"\n\n⏳ 𝐑𝐞𝐦𝐚𝐢𝐧𝐢𝐧𝐠 𝐃𝐚𝐲𝐬 : <b>{remaining_days}</b>"
    return txt

def build_summary(total, success, failed, total_likes, failed_uids):
    txt = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  📊 𝐀𝐔𝐓𝐎 𝐋𝐈𝐊𝐄 𝐒𝐔𝐌𝐌𝐀𝐑𝐘 📊\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        f"🎯 𝐓𝐨𝐭𝐚𝐥       : <b>{total}</b>\n"
        f"✅ 𝐒𝐮𝐜𝐜𝐞𝐬𝐬      : <b>{success}</b>\n"
        f"❌ 𝐅𝐚𝐢𝐥𝐞𝐝       : <b>{failed}</b>\n"
        f"❤️ 𝐓𝐨𝐭𝐚𝐥 𝐋𝐢𝐤𝐞𝐬 : <b>{fmt_num(total_likes)}</b> 🧩\n"
        f"🕓 𝐑𝐮𝐧 𝐓𝐢𝐦𝐞    : <b>{get_india_time().strftime('%d-%b-%Y %I:%M %p')} IST</b>"
    )
    if failed_uids:
        txt += "\n\n⚠️ 𝐅𝐚𝐢𝐥𝐞𝐝 𝐔𝐈𝐃𝐬\n" + "\n".join(
            [f"• <code>{u}</code>" for u in failed_uids[:15]]
        )
    return txt

# ==============================================================================
#             NETWORK REQUESTS
# ==============================================================================
LIKE_API_URL = "https://like-api-by-kamod.onrender.com/like"

def call_like_api(uid, region="ind"):
    response = requests.get(
        LIKE_API_URL,
        params={"uid": str(uid), "server_name": str(region).lower()},
        timeout=45,
    )
    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        return {"message": response.text, "http_status": response.status_code}

def api_result_values(data, before=0):
    if not isinstance(data, dict):
        return False, 0, before, before, "Unexpected API response", "Unknown"
    raw_status = data.get("status", data.get("success", False))
    if isinstance(raw_status, (int, float)):
        success_flag = raw_status == 2 or raw_status == 200
    elif isinstance(raw_status, str):
        success_flag = raw_status.strip().lower() in {"2", "200", "true", "success", "ok"}
    else:
        success_flag = bool(raw_status)
    added = data.get("LikesGivenByAPI", data.get("added", data.get("likes_added", data.get("success_count", data.get("likes_sent", 0)))))
    reported_before = data.get("LikesbeforeCommand", data.get("before", before))
    after = data.get("LikesafterCommand", data.get("after", data.get("total_likes", data.get("likes", None))))
    nickname = str(data.get("PlayerNickname", data.get("name", data.get("nickname", "Unknown"))) or "Unknown")
    try:
        added = int(added or 0)
    except:
        added = 0
    try:
        reported_before = int(reported_before if reported_before is not None else before)
    except:
        reported_before = before
    try:
        after = int(after) if after is not None else reported_before + added
    except:
        after = reported_before + added
    message = str(data.get("message", data.get("msg", data.get("error", ""))))
    if not success_flag and (added > 0 or after > reported_before):
        success_flag = True
    return success_flag, added, reported_before, after, message, nickname

# ==============================================================================
#             LIKE TASK
# ==============================================================================
async def process_like_task(chat_id, uid, region, context, msg_id, user_id, is_premium, today_used):
    if region.lower() != "ind":
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=("╔════════════════════╗\n"
                      "      🚫 𝐒𝐄𝐑𝐕𝐄𝐑 𝐄𝐑𝐑𝐎𝐑\n"
                      "╚════════════════════╝\n\n"
                      "✅ Use IND server only.\n\n"
                      "Example: /like ind 7737005533")
            )
        except Exception:
            pass
        return

    try:
        for percent in [0, 40, 80, 100]:
            bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=("⚡ <b>𝐊𝐀𝐌𝐎𝐃 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐂𝐎𝐍𝐒𝐎𝐋𝐄</b> ⚡\n"
                      "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                      f"👤 𝐔𝐈𝐃 : <code>{html.escape(str(uid))}</code>\n"
                      f"<code>{bar} {percent}%</code>\n\n"
                      "🚀 𝐏𝐫𝐨𝐜𝐞𝐬𝐬𝐢𝐧𝐠..."),
                parse_mode="HTML"
            )
            await asyncio.sleep(0.25)
    except Exception:
        pass

    try:
        api_data = await asyncio.to_thread(call_like_api, uid, region)
        success_flag, added, before, after, api_message, player_name = api_result_values(api_data, 0)
    except Exception as e:
        success_flag, added, before, after, player_name = False, 0, 0, 0, "Unknown"
        api_message = str(e)

    keyboard = [[
        InlineKeyboardButton("👑 𝐎𝐖𝐍𝐄𝐑", url="https://t.me/kamod90"),
        InlineKeyboardButton("📢 𝐌𝐀𝐈𝐍 𝐂𝐇𝐀𝐍𝐍𝐄𝐋", url="https://t.me/KAMOD_CODEX"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if not success_flag:
        msg_text = build_like_fail(player_name, uid, region, before, added, after, api_message)
    else:
        if not is_premium:
            with DATA_LOCK:
                get_data()["cooldowns"].setdefault(str(user_id), []).append({
                    "uid": str(uid), "time": get_india_time().isoformat()
                })
        msg_text = build_like_success(player_name, uid, region, before, added, after)

    with DATA_LOCK:
        get_data().setdefault("like_history", {}).setdefault(str(user_id), []).append({
            "uid": str(uid), "player": player_name, "region": region,
            "before": before, "added": added, "after": after,
            "time": get_india_time().isoformat(), "ok": success_flag
        })

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id, text=msg_text,
            parse_mode="HTML", reply_markup=reply_markup
        )
    except Exception:
        pass

# ==============================================================================
#             AUTO LIKE — 4:00 AM IST + SUMMARY
# ==============================================================================
async def auto_like_job(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    now = get_india_time()
    today_date = now.strftime("%Y-%m-%d")

    if now.hour != AUTOLIKE_RUN_HOUR or now.minute > 4:
        return

    tasks_to_run = []
    with DATA_LOCK:
        for task in get_data().get("autolike", []):
            if task["last_run"] != today_date and task["days"] > 0:
                tasks_to_run.append(task)

    if not tasks_to_run:
        return

    total = len(tasks_to_run)
    success = 0
    failed = 0
    total_likes = 0
    failed_uids = []

    for task in tasks_to_run:
        await process_auto_like_task(app, task, today_date)
        res = task.get("_last_result", {})
        if res.get("ok"):
            success += 1
            total_likes += res.get("added", 0)
        else:
            failed += 1
            failed_uids.append(task["uid"])

    summary = build_summary(total, success, failed, total_likes, failed_uids)
    try:
        await app.bot.send_message(chat_id=GROUP_LINK, text=summary, parse_mode="HTML")
    except Exception as e:
        print("Summary send failed:", e)

    with DATA_LOCK:
        get_data()["daily_summary"][today_date] = {
            "total": total, "success": success, "failed": failed,
            "likes": total_likes, "time": now.isoformat()
        }

def is_admin(user_id):
    if user_id == ADMIN_ID:
        return True
    admin_data = get_data().get("admins", {})
    expiry = admin_data.get(str(user_id))
    if not expiry:
        return False
    try:
        if datetime.fromisoformat(expiry) > datetime.now():
            return True
        else:
            del admin_data[str(user_id)]
            return False
    except:
        return False

async def process_auto_like_task(app, task, today_date):
    try:
        api_data = await asyncio.to_thread(call_like_api, task["uid"], task["region"])
        success_flag, added, before, after, api_message, player_name = api_result_values(api_data, 0)

        with DATA_LOCK:
            task["last_run"] = today_date
            task["days"] -= 1
            task["_last_result"] = {"ok": success_flag, "added": added}
            if task["days"] <= 0:
                try:
                    get_data()["autolike"].remove(task)
                except ValueError:
                    pass

        owner_id = task.get("owner", ADMIN_ID)
        plan_label = "👑 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐋𝐈𝐊𝐄" if is_admin(owner_id) else "🆓 𝐅𝐑𝐄𝐄 𝐋𝐈𝐊𝐄"
        msg = build_auto_like(
            player_name, task["uid"], task["region"],
            before, added, after, plan_label,
            remaining_days=task["days"], status_ok=success_flag
        )
        try:
            await app.bot.send_message(chat_id=GROUP_LINK, text=msg, parse_mode="HTML")
        except Exception:
            pass
    except Exception as e:
        print("AutoLike API Error:", e)
        with DATA_LOCK:
            task["_last_result"] = {"ok": False, "added": 0}

# ==============================================================================
#             COMMAND HANDLERS
# ==============================================================================
async def check_subscription(user_id, context):
    if user_id == ADMIN_ID:
        return True
    not_joined = []
    for channel in MUST_JOIN_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in [ChatMember.LEFT, ChatMember.BANNED, ChatMember.RESTRICTED]:
                not_joined.append(channel)
        except:
            pass
    return len(not_joined) == 0

async def force_join_alert(update, context):
    keyboard = [
        [InlineKeyboardButton("📢 𝐉𝐎𝐈𝐍 𝐂𝐇𝐀𝐍𝐍𝐄𝐋 𝐍𝐎𝐖", url=f"https://t.me/{CHANNEL_LINK.replace('@','')}")],
        [InlineKeyboardButton("✅ 𝐕𝐄𝐑𝐈𝐅𝐘 & 𝐓𝐑𝐘 𝐀𝐆𝐀𝐈𝐍", callback_data="check_join")]
    ]
    msg = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  🚨 𝐀𝐂𝐂𝐄𝐒𝐒 𝐑𝐄𝐐𝐔𝐈𝐑𝐄𝐃\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "𝐉𝐨𝐢𝐧 𝐨𝐟𝐟𝐢𝐜𝐢𝐚𝐥 𝐜𝐡𝐚𝐧𝐧𝐞𝐥\n"
        "𝐛𝐞𝐟𝐨𝐫𝐞 𝐮𝐬𝐢𝐧𝐠 𝐭𝐡𝐢𝐬 𝐛𝐨𝐭.\n\n"
        "╭━⟮ ✦ 𝐒𝐓𝐄𝐏𝐒 ✦ ⟯\n"
        "│  1️⃣ 𝐉𝐨𝐢𝐧 𝐂𝐡𝐚𝐧𝐧𝐞𝐥\n"
        "│  2️⃣ 𝐂𝐥𝐢𝐜𝐤 𝐕𝐞𝐫𝐢𝐟𝐲\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        f"👑 𝐎𝐰𝐧𝐞𝐫 : {OWNER_LINK}"
    )
    if update.callback_query:
        await update.callback_query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user if update.effective_user else update.callback_query.from_user
    record_user(user)
    if not await check_subscription(user.id, context):
        return await force_join_alert(update, context)
    safe_name = html.escape(user.first_name)
    poster = (
        "⚡ 𝐊𝐀𝐌𝐎𝐃 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐂𝐎𝐍𝐒𝐎𝐋𝐄 ⚡\n"
        " 𝐯𝟑.𝟎 | 𝐒𝐭𝐚𝐭𝐮𝐬: 𝐎𝐧𝐥𝐢𝐧𝐞 🟢\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 𝐇𝐞𝐲 <b>{safe_name}</b>!\n"
        "🚀 <i>𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐭𝐨 𝐭𝐡𝐞 𝐔𝐥𝐭𝐢𝐦𝐚𝐭𝐞 𝐅𝐅 𝐓𝐨𝐨𝐥.</i>\n\n"
        "💠 <b>𝐌𝐚𝐢𝐧 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬:</b>\n"
        "👍 <code>𝐀𝐮𝐭𝐨 𝐋𝐢𝐤𝐞</code>  |  👁️ <code>𝐀𝐮𝐭𝐨 𝐕𝐢𝐬𝐢𝐭</code>\n"
        "📊 <code>𝐑𝐚𝐧𝐤 𝐏𝐮𝐬𝐡</code>  |  🛡️ <code>𝐀𝐧𝐭𝐢-𝐁𝐚𝐧</code>\n\n"
        "👇 <b>𝐂𝐥𝐢𝐜𝐤 𝐂𝐨𝐦𝐦𝐚𝐧𝐝 𝐋𝐢𝐬𝐭 𝐭𝐨 𝐁𝐞𝐠𝐢𝐧:</b>"
    )
    kb = [
        [InlineKeyboardButton("📜 𝐂𝐎𝐌𝐌𝐀𝐍𝐃 𝐋𝐈𝐒𝐓", callback_data="show_help")],
        [InlineKeyboardButton("🆘 𝐒𝐔𝐏𝐏𝐎𝐑𝐓", url=f"https://t.me/{OWNER_LINK.replace('@', '')}")]
    ]
    if update.callback_query:
        try:
            await update.callback_query.message.edit_text(poster, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=poster, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=poster, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await check_subscription(query.from_user.id, context):
        await query.answer("✅ 𝐀𝐜𝐜𝐞𝐬𝐬 𝐆𝐫𝐚𝐧𝐭𝐞𝐝!")
        try:
            await query.message.delete()
        except:
            pass
        await help_command(update, context)
    else:
        await query.answer("❌ 𝐉𝐨𝐢𝐧 𝐧𝐚𝐡𝐢 𝐤𝐢𝐲𝐚!", show_alert=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update.effective_user.id, context):
        return await force_join_alert(update, context)
    help_text = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  📜 𝐂𝐎𝐌𝐌𝐀𝐍𝐃 𝐂𝐄𝐍𝐓𝐄𝐑\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 👤 𝐔𝐒𝐄𝐑 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒 ✦ ⟯\n"
        "│  ❤️  /like 𝐈𝐍𝐃 𝐔𝐈𝐃\n"
        "│  👁️  /visit 𝐈𝐍𝐃 𝐔𝐈𝐃\n"
        "│  💎  /myplan\n"
        "│  📜  /mylikes\n"
        "│  ⏳  /cooldown\n"
        "│  🔍  /uidinfo 𝐔𝐈𝐃\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 🛡️ 𝐀𝐃𝐌𝐈𝐍 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒 ✦ ⟯\n"
        "│  ➕  /adduser 𝐈𝐃 𝐃𝐚𝐲𝐬\n"
        "│  ➖  /removeuser 𝐈𝐃\n"
        "│  👑  /addadmin 𝐈𝐃 𝐃𝐚𝐲𝐬\n"
        "│  ❌  /removeadmin 𝐈𝐃\n"
        "│  🤖  /autolike 𝐈𝐍𝐃 𝐔𝐈𝐃 𝐃𝐚𝐲𝐬\n"
        "│  📊  /status\n"
        "│  📢  /broadcast 𝐌𝐞𝐬𝐬𝐚𝐠𝐞\n"
        "│  📋  /allliststatus\n"
        "│  📊  /summary\n"
        "│  ⚙️  /maintenance 𝐨𝐧/𝐨𝐟𝐟\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        f"👑 𝐎𝐰𝐧𝐞𝐫 : {OWNER_LINK}"
    )
    kb = [[InlineKeyboardButton("💬 𝐂𝐎𝐍𝐓𝐀𝐂𝐓 𝐒𝐔𝐏𝐏𝐎𝐑𝐓", url=f"https://t.me/{OWNER_LINK.replace('@', '')}")]]
    if update.callback_query:
        await update.callback_query.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    else:
        await context.bot.send_message(update.effective_chat.id, text=help_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def mylikes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await check_subscription(user.id, context):
        return await force_join_alert(update, context)
    hist = get_data().get("like_history", {}).get(str(user.id), [])[-10:]
    if not hist:
        return await update.message.reply_text("📜 𝐍𝐨 𝐥𝐢𝐤𝐞 𝐡𝐢𝐬𝐭𝐨𝐫𝐲 𝐲𝐞𝐭.")
    lines = []
    for h in reversed(hist):
        icon = "✅" if h["ok"] else "❌"
        t = h["time"][:16].replace("T", " ")
        lines.append(f"{icon} <code>{h['uid']}</code> | {h['region']} | +{h['added']} ❤️ | {t}")
    await update.message.reply_text(
        "╭━━━━━━━━━━━━━━━━━━━━✪\n│  📜 𝐋𝐈𝐊𝐄 𝐇𝐈𝐒𝐓𝐎𝐑𝐘 (𝐋𝐚𝐬𝐭 𝟏𝟎)\n╰━━━━━━━━━━━━━━━━━━━━✪\n\n" + "\n".join(lines),
        parse_mode="HTML"
    )

async def cooldown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await check_subscription(user.id, context):
        return await force_join_alert(update, context)
    data = get_data()
    if str(user.id) in data["premium"]:
        return await update.message.reply_text("👑 <b>𝐏𝐑𝐄𝐌𝐈𝐔𝐌</b> — 𝐍𝐨 𝐜𝐨𝐨𝐥𝐝𝐨𝐰𝐧 🚀", parse_mode="HTML")
    history = data["cooldowns"].get(str(user.id), [])
    valid = []
    for e in history:
        try:
            if get_india_time() - datetime.fromisoformat(e["time"]) < timedelta(hours=24):
                valid.append(e)
        except:
            pass
    if not valid:
        return await update.message.reply_text("✅ 𝐘𝐨𝐮 𝐡𝐚𝐯𝐞 𝐧𝐨 𝐚𝐜𝐭𝐢𝐯𝐞 𝐜𝐨𝐨𝐥𝐝𝐨𝐰𝐧.")
    lines = []
    for v in valid:
        unlock = datetime.fromisoformat(v["time"]) + timedelta(hours=24)
        rem = unlock - get_india_time()
        h, r = divmod(int(rem.total_seconds()), 3600)
        m, _ = divmod(r, 60)
        lines.append(f"⏳ 𝐔𝐈𝐃 <code>{v['uid']}</code> — {h}h {m}m 𝐥𝐞𝐟𝐭")
    await update.message.reply_text(
        "╭━━━━━━━━━━━━━━━━━━━━✪\n│  ⏳ 𝐀𝐂𝐓𝐈𝐕𝐄 𝐂𝐎𝐎𝐋𝐃𝐎𝐖𝐍𝐒\n╰━━━━━━━━━━━━━━━━━━━━✪\n\n" + "\n".join(lines),
        parse_mode="HTML"
    )

async def uidinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        return await update.message.reply_text("❌ 𝐔𝐬𝐚𝐠𝐞: /uidinfo 𝐔𝐈𝐃", parse_mode="HTML")
    uid = context.args[0]
    link = f"https://ff.garena.com/en/profile/{uid}/"
    await update.message.reply_text(
        "╭━━━━━━━━━━━━━━━━━━━━✪\n│  🔍 𝐔𝐈𝐃 𝐈𝐍𝐅𝐎\n╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        f"🆔 𝐔𝐈𝐃 : <code>{html.escape(uid)}</code>\n"
        f"🔗 𝐏𝐫𝐨𝐟𝐢𝐥𝐞 : {link}",
        parse_mode="HTML"
    )

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("🚫 𝐀𝐝𝐦𝐢𝐧 𝐎𝐧𝐥𝐲")
    ds = get_data().get("daily_summary", {})
    if not ds:
        return await update.message.reply_text("📊 𝐍𝐨 𝐬𝐮𝐦𝐦𝐚𝐫𝐲 𝐲𝐞𝐭. 𝐀𝐮𝐭𝐨 𝐥𝐢𝐤𝐞 𝐫𝐮𝐧𝐬 𝐚𝐭 𝟒 𝐀𝐌 𝐈𝐒𝐓.")
    last_date = sorted(ds.keys())[-1]
    s = ds[last_date]
    msg = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        f"│  📊 𝐒𝐔𝐌𝐌𝐀𝐑𝐘 — {last_date}\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        f"🎯 𝐓𝐨𝐭𝐚𝐥   : <b>{s['total']}</b>\n"
        f"✅ 𝐒𝐮𝐜𝐜𝐞𝐬𝐬 : <b>{s['success']}</b>\n"
        f"❌ 𝐅𝐚𝐢𝐥𝐞𝐝  : <b>{s['failed']}</b>\n"
        f"❤️ 𝐋𝐢𝐤𝐞𝐬   : <b>{fmt_num(s['likes'])}</b> 🧩"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def like_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    record_user(user)
    if get_data().get("maintenance") and user.id != ADMIN_ID:
        return await update.message.reply_text("🚧 <b>𝐌𝐀𝐈𝐍𝐓𝐄𝐍𝐀𝐍𝐂𝐄 𝐌𝐎𝐃𝐄!</b>", parse_mode="HTML")
    if not await check_subscription(user.id, context):
        return await force_join_alert(update, context)

    if update.effective_chat.type == "private" and user.id != ADMIN_ID:
        group_only_msg = (
            "╭━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "│   ❌ 𝐂𝐎𝐌𝐌𝐀𝐍𝐃 𝐍𝐎𝐓 𝐀𝐕𝐀𝐈𝐋𝐀𝐁𝐋𝐄   │\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "╭━⟮ ⚠️ 𝐀𝐂𝐂𝐄𝐒𝐒 𝐑𝐄𝐒𝐓𝐑𝐈𝐂𝐓𝐄𝐃 ⟯━╮\n"
            "│  𝐓𝐡𝐢𝐬 𝐜𝐨𝐦𝐦𝐚𝐧𝐝 𝐰𝐨𝐫𝐤𝐬 𝐨𝐧𝐥𝐲\n"
            "│  𝐢𝐧𝐬𝐢𝐝𝐞 𝐭𝐡𝐞 𝐨𝐟𝐟𝐢𝐜𝐢𝐚𝐥 𝐠𝐫𝐨𝐮𝐩.\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "👥 𝐉𝐨𝐢𝐧 𝐎𝐟𝐟𝐢𝐜𝐢𝐚𝐥 𝐆𝐫𝐨𝐮𝐩 𝐁𝐞𝐥𝐨𝐰"
        )
        keyboard = [[InlineKeyboardButton("👥 𝐉𝐎𝐈𝐍 𝐎𝐅𝐅𝐈𝐂𝐈𝐀𝐋 𝐆𝐑𝐎𝐔𝐏", url=f"https://t.me/{GROUP_LINK.replace('@','')}")]]
        return await update.message.reply_text(group_only_msg, reply_markup=InlineKeyboardMarkup(keyboard))

    if len(context.args) != 2:
        return await update.message.reply_text("❌ <b>𝐔𝐬𝐚𝐠𝐞:</b> <code>/like IND 12345678</code>", parse_mode="HTML")

    data = get_data()
    is_premium = str(user.id) in data["premium"] or user.id == ADMIN_ID
    if is_premium and str(user.id) in data["premium"]:
        try:
            if datetime.fromisoformat(data["premium"][str(user.id)]) < datetime.now():
                is_premium = False
        except:
            is_premium = False

    today_used = 0
    if not is_premium:
        history = data["cooldowns"].get(str(user.id), [])
        valid = []
        for e in history:
            try:
                if get_india_time() - datetime.fromisoformat(e["time"]) < timedelta(hours=24):
                    valid.append(e)
            except:
                pass
        data["cooldowns"][str(user.id)] = valid
        today_used = len(valid)
        for entry in valid:
            if entry["uid"] == context.args[1]:
                last_used = datetime.fromisoformat(entry["time"])
                unlock_at = last_used + timedelta(hours=24)
                remaining = unlock_at - get_india_time()
                if remaining.total_seconds() > 0:
                    hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                    minutes, _ = divmod(remainder, 60)
                    cooldown_msg = (
                        "╭━━━━━━━━━━━━━━━━━╮\n│ ⛔  𝐂𝐎𝐎𝐋𝐃𝐎𝐖𝐍 𝐀𝐂𝐓𝐈𝐕𝐄 │\n╰━━━━━━━━━━━━━━━━━╯\n\n"
                        "╭━⟮ ⚠️ 𝐒𝐓𝐀𝐓𝐔𝐒 ⟯━╮\n│  𝐔𝐈𝐃 𝐚𝐥𝐫𝐞𝐚𝐝𝐲 𝐫𝐞𝐜𝐞𝐢𝐯𝐞𝐝\n│  𝐥𝐢𝐤𝐞𝐬 𝐭𝐨𝐝𝐚𝐲.\n╰━━━━━━━━━━━━━━╯\n\n"
                        "╭━⟮ ⏳ 𝐓𝐈𝐌𝐄 𝐋𝐄𝐅𝐓 ⟯━╮\n"
                        f"│  {hours}h {minutes}m 𝐫𝐞𝐦𝐚𝐢𝐧𝐢𝐧𝐠\n"
                        "╰━━━━━━━━━━━━━━╯"
                    )
                    return await update.message.reply_text(cooldown_msg)
        if len(valid) >= 2:
            limit_msg = (
                "╭━━━━━━━━━━━━━━━━━━╮\n│  𝐃𝐀𝐈𝐋𝐘 𝐋𝐈𝐌𝐈𝐓 𝐑𝐄𝐀𝐂𝐇𝐄𝐃   │\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
                "╭━⟮ 📊 𝐋𝐈𝐌𝐈𝐓 𝐈𝐍𝐅𝐎 ⟯━╮\n│  𝐅𝐫𝐞𝐞 𝐮𝐬𝐞𝐫𝐬 𝐜𝐚𝐧 𝐬𝐞𝐧𝐝\n│  𝐨𝐧𝐥𝐲 𝟐 𝐮𝐢𝐝 𝐥𝐢𝐤𝐞𝐬 𝐩𝐞𝐫 𝐝𝐚𝐲.\n╰━━━━━━━━━━━━━━╯\n\n"
                f"👑 𝐔𝐩𝐠𝐫𝐚𝐝𝐞 𝐭𝐨 𝐏𝐑𝐄𝐌𝐈𝐔𝐌\n📩 {OWNER_LINK}"
            )
            return await update.message.reply_text(limit_msg)

    msg = await update.message.reply_text("❤️ <b>𝐒𝐞𝐧𝐝𝐢𝐧𝐠 𝐋𝐢𝐤𝐞𝐬...</b>", parse_mode="HTML")
    asyncio.create_task(
        process_like_task(
            update.effective_chat.id, context.args[1], context.args[0].upper(),
            context, msg.message_id, user.id, is_premium, today_used
        )
    )

async def autolike_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("🚫 𝐀𝐝𝐦𝐢𝐧 𝐎𝐧𝐥𝐲")
    if len(context.args) != 3:
        return await update.message.reply_text(
            "❌ 𝐔𝐬𝐚𝐠𝐞: /autolike 𝐈𝐍𝐃 <𝐔𝐈𝐃> <𝐃𝐚𝐲𝐬>\n"
            "⏰ 𝐀𝐮𝐭𝐨 𝐋𝐢𝐤𝐞 𝐫𝐮𝐧𝐬 𝐝𝐚𝐢𝐥𝐲 𝐚𝐭 𝟒:𝟎𝟎 𝐀𝐌 𝐈𝐒𝐓.\n"
            "𝐄𝐱𝐚𝐦𝐩𝐥𝐞: /autolike 𝐈𝐍𝐃 𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖 𝟕"
        )
    region = context.args[0].upper()
    uid = context.args[1]
    try:
        days = int(context.args[2])
    except:
        return await update.message.reply_text("❌ 𝐃𝐚𝐲𝐬 𝐦𝐮𝐬𝐭 𝐛𝐞 𝐧𝐮𝐦𝐛𝐞𝐫")

    new_task = {
        "region": region, "uid": uid,
        "time": "04:00 AM", "days": days,
        "last_run": "", "owner": update.effective_user.id
    }
    with DATA_LOCK:
        get_data()["autolike"].append(new_task)

    now = get_india_time()
    start_date = now.strftime("%d-%b-%Y")
    expiry_date = (now + timedelta(days=days)).strftime("%d-%b-%Y")
    msg = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  🤖 𝐀𝐔𝐓𝐎 𝐋𝐈𝐊𝐄 𝐀𝐂𝐓𝐈𝐕𝐀𝐓𝐄𝐃\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 👤 𝐏𝐋𝐀𝐘𝐄𝐑 𝐃𝐄𝐓𝐀𝐈𝐋𝐒 ✦ ⟯\n"
        f"│  🎯 𝐔𝐈𝐃     : <code>{uid}</code>\n"
        f"│  🌍 𝐑𝐞𝐠𝐢𝐨𝐧  : <b>{region}</b>\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ ⏰ 𝐒𝐂𝐇𝐄𝐃𝐔𝐋𝐄 ✦ ⟯\n"
        f"│  📅 𝐒𝐭𝐚𝐫𝐭 𝐃𝐚𝐭𝐞  : <b>{start_date}</b>\n"
        f"│  📅 𝐄𝐱𝐩𝐢𝐫𝐲 𝐃𝐚𝐭𝐞 : <b>{expiry_date}</b>\n"
        f"│  ⏰ 𝐃𝐚𝐢𝐥𝐲 𝐓𝐢𝐦𝐞  : <b>𝟎𝟒:𝟎𝟎 𝐀𝐌 𝐈𝐒𝐓</b>\n"
        f"│  📆 𝐓𝐨𝐭𝐚𝐥 𝐃𝐚𝐲𝐬  : <b>{days}</b>\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 🚀 𝐒𝐓𝐀𝐓𝐔𝐒 ✦ ⟯\n"
        "│  𝐀𝐮𝐭𝐨 𝐋𝐢𝐤𝐞 𝐄𝐧𝐠𝐢𝐧𝐞 : <b>𝐀𝐂𝐓𝐈𝐕𝐄</b> 🟢\n"
        "│  𝐄𝐱𝐞𝐜𝐮𝐭𝐢𝐨𝐧 𝐌𝐨𝐝𝐞   : 𝐀𝐮𝐭𝐨𝐦𝐚𝐭𝐢𝐜\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        f"💎 𝐌𝐚𝐧𝐚𝐠𝐞𝐝 𝐛𝐲 {OWNER_LINK}"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("🚫 𝐀𝐝𝐦𝐢𝐧 𝐎𝐧𝐥𝐲")
    data = get_data()
    msg_text = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  📊 𝐒𝐘𝐒𝐓𝐄𝐌 𝐌𝐎𝐍𝐈𝐓𝐎𝐑\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 👥 𝐔𝐒𝐄𝐑𝐒 ✦ ⟯\n"
        f"│  👥 𝐓𝐨𝐭𝐚𝐥    : <b>{len(data['all_users'])}</b>\n"
        f"│  💎 𝐏𝐫𝐞𝐦𝐢𝐮𝐦  : <b>{len(data['premium'])}</b>\n"
        f"│  🛡 𝐀𝐝𝐦𝐢𝐧𝐬   : <b>{len(data.get('admins', {}))}</b>\n"
        f"│  🤖 𝐀𝐮𝐭𝐨𝐥𝐢𝐤𝐞 : <b>{len(data['autolike'])}</b>\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        "⚡ 𝐋𝐢𝐤𝐞 𝐒𝐲𝐬𝐭𝐞𝐦 : 𝐀𝐏𝐈\n"
        "⚡ 𝐁𝐨𝐭 𝐒𝐭𝐚𝐭𝐮𝐬  : 𝐎𝐧𝐥𝐢𝐧𝐞 🟢\n"
        f"👑 𝐎𝐰𝐧𝐞𝐫 : {OWNER_LINK}"
    )
    await update.message.reply_text(msg_text, parse_mode="HTML")

async def allliststatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("🚫 𝐀𝐝𝐦𝐢𝐧 𝐎𝐧𝐥𝐲")
    data = get_data()
    with DATA_LOCK:
        autolike_list = data.get("autolike", [])
        premium_users = data.get("premium", {})
        admin_users = data.get("admins", {})
    auto_text = "\n".join([f"🎯 𝐔𝐈𝐃: {t['uid']} | 🌍 {t['region']}" for t in autolike_list]) if autolike_list else "𝐍𝐨 𝐀𝐮𝐭𝐨𝐋𝐢𝐤𝐞 𝐀𝐜𝐭𝐢𝐯𝐞"
    premium_text = "\n".join([f"👑 {uid}" for uid in premium_users.keys()]) if premium_users else "𝐍𝐨 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐔𝐬𝐞𝐫𝐬"
    admin_text = "\n".join([f"🛡 {uid}" for uid in admin_users.keys()]) if admin_users else "𝐍𝐨 𝐀𝐝𝐦𝐢𝐧𝐬"
    msg = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  📋 𝐀𝐋𝐋 𝐋𝐈𝐒𝐓 𝐒𝐓𝐀𝐓𝐔𝐒\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "📌 𝐀𝐔𝐓𝐎 𝐋𝐈𝐊𝐄 𝐋𝐈𝐒𝐓:\n"
        f"{auto_text}\n\n"
        "👑 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐔𝐒𝐄𝐑𝐒:\n"
        f"{premium_text}\n\n"
        "🛡 𝐀𝐃𝐌𝐈𝐍 𝐔𝐒𝐄𝐑𝐒:\n"
        f"{admin_text}"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 𝐎𝐧𝐥𝐲 𝐎𝐰𝐧𝐞𝐫 𝐂𝐚𝐧 𝐔𝐬𝐞 𝐓𝐡𝐢𝐬 𝐂𝐨𝐦𝐦𝐚𝐧𝐝")
    if len(context.args) != 2:
        return await update.message.reply_text("❌ 𝐔𝐬𝐚𝐠𝐞: /addadmin 𝐔𝐒𝐄𝐑_𝐈𝐃 𝐃𝐚𝐲𝐬", parse_mode="HTML")
    user_id = context.args[0]
    try:
        days = int(context.args[1])
    except:
        return await update.message.reply_text("❌ 𝐃𝐚𝐲𝐬 𝐦𝐮𝐬𝐭 𝐛𝐞 𝐧𝐮𝐦𝐛𝐞𝐫")
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    expiry_fmt = (datetime.now() + timedelta(days=days)).strftime("%d-%b-%Y")
    with DATA_LOCK:
        get_data()["admins"][str(user_id)] = expiry
    msg = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  👑 𝐀𝐃𝐌𝐈𝐍 𝐀𝐂𝐂𝐄𝐒𝐒 𝐆𝐑𝐀𝐍𝐓𝐄𝐃\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 👤 𝐀𝐃𝐌𝐈𝐍 𝐃𝐄𝐓𝐀𝐈𝐋𝐒 ✦ ⟯\n"
        f"│  🆔 𝐔𝐬𝐞𝐫 𝐈𝐃     : <code>{user_id}</code>\n"
        f"│  👑 𝐑𝐨𝐥𝐞        : 𝐀𝐝𝐦𝐢𝐧𝐢𝐬𝐭𝐫𝐚𝐭𝐨𝐫\n"
        f"│  ⏳ 𝐕𝐚𝐥𝐢𝐝 𝐅𝐨𝐫   : <b>{days} 𝐃𝐚𝐲𝐬</b>\n"
        f"│  📅 𝐄𝐱𝐩𝐢𝐫𝐲 𝐃𝐚𝐭𝐞 : <b>{expiry_fmt}</b>\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 🔐 𝐏𝐄𝐑𝐌𝐈𝐒𝐒𝐈𝐎𝐍𝐒 ✦ ⟯\n"
        "│  ✓ 𝐀𝐮𝐭𝐨 𝐋𝐢𝐤𝐞 𝐂𝐨𝐧𝐭𝐫𝐨𝐥\n"
        "│  ✓ 𝐒𝐭𝐚𝐭𝐮𝐬 𝐀𝐜𝐜𝐞𝐬𝐬\n"
        "│  ✓ 𝐁𝐫𝐨𝐚𝐝𝐜𝐚𝐬𝐭 𝐀𝐜𝐜𝐞𝐬𝐬\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        f"👑 𝐆𝐫𝐚𝐧𝐭𝐞𝐝 𝐁𝐲 : {OWNER_LINK}"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 𝐎𝐧𝐥𝐲 𝐎𝐰𝐧𝐞𝐫 𝐂𝐚𝐧 𝐔𝐬𝐞 𝐓𝐡𝐢𝐬 𝐂𝐨𝐦𝐦𝐚𝐧𝐝")
    if len(context.args) != 1:
        return await update.message.reply_text("❌ 𝐔𝐬𝐚𝐠𝐞: /removeadmin 𝐔𝐒𝐄𝐑_𝐈𝐃", parse_mode="HTML")
    user_id = context.args[0]
    with DATA_LOCK:
        if str(user_id) not in get_data()["admins"]:
            return await update.message.reply_text("❌ 𝐔𝐬𝐞𝐫 𝐍𝐨𝐭 𝐀𝐝𝐦𝐢𝐧")
        del get_data()["admins"][str(user_id)]
    msg = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  ❌ 𝐀𝐃𝐌𝐈𝐍 𝐀𝐂𝐂𝐄𝐒𝐒 𝐑𝐄𝐕𝐎𝐊𝐄𝐃\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 👤 𝐀𝐃𝐌𝐈𝐍 𝐃𝐄𝐓𝐀𝐈𝐋𝐒 ✦ ⟯\n"
        f"│  🆔 𝐔𝐬𝐞𝐫 𝐈𝐃 : <code>{user_id}</code>\n"
        f"│  👑 𝐑𝐨𝐥𝐞    : 𝐀𝐝𝐦𝐢𝐧𝐢𝐬𝐭𝐫𝐚𝐭𝐨𝐫\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ ⚠️ 𝐒𝐓𝐀𝐓𝐔𝐒 𝐔𝐏𝐃𝐀𝐓𝐄 ✦ ⟯\n"
        "│  𝐀𝐜𝐜𝐞𝐬𝐬 : 𝐑𝐞𝐦𝐨𝐯𝐞𝐝\n"
        "│  𝐏𝐚𝐧𝐞𝐥  : 𝐃𝐢𝐬𝐚𝐛𝐥𝐞𝐝\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        f"🔒 𝐑𝐞𝐦𝐨𝐯𝐞𝐝 𝐁𝐲 : {OWNER_LINK}"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def myplan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_data()
    user = update.effective_user
    user_id = str(user.id)
    safe_name = html.escape(user.first_name)
    if user_id in data["premium"]:
        try:
            exp_date = datetime.fromisoformat(data["premium"][user_id])
            days_left = (exp_date - datetime.now()).days
            expiry_fmt = exp_date.strftime('%d-%b-%Y')
        except:
            expiry_fmt = "Unknown"
            days_left = 0
        msg = (
            "╭━━━━━━━━━━━━━━━━━━━━✪\n"
            "│  💎 𝐕𝐈𝐏 𝐃𝐀𝐒𝐇𝐁𝐎𝐀𝐑𝐃\n"
            "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 👤 𝐀𝐂𝐂𝐎𝐔𝐍𝐓 𝐈𝐍𝐅𝐎 ✦ ⟯\n"
            f"│  👤 𝐔𝐬𝐞𝐫   : <b>{safe_name}</b>\n"
            "│  💎 𝐏𝐥𝐚𝐧   : <b>𝐏𝐫𝐞𝐦𝐢𝐮𝐦</b>\n"
            f"│  📅 𝐄𝐱𝐩𝐢𝐫𝐲 : <b>{expiry_fmt}</b>\n"
            f"│  ⏳ 𝐃𝐚𝐲𝐬   : <b>{days_left}</b>\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 🚀 𝐁𝐄𝐍𝐄𝐅𝐈𝐓𝐒 ✦ ⟯\n"
            "│  ✓ 𝐔𝐧𝐥𝐢𝐦𝐢𝐭𝐞𝐝 𝐋𝐢𝐤𝐞𝐬\n"
            "│  ✓ 𝐍𝐨 𝐂𝐨𝐨𝐥𝐝𝐨𝐰𝐧\n"
            "│  ✓ 𝐏𝐫𝐢𝐨𝐫𝐢𝐭𝐲 𝐀𝐜𝐜𝐞𝐬𝐬\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            f"👑 𝐄𝐥𝐢𝐭𝐞 𝐌𝐞𝐦𝐛𝐞𝐫 • {OWNER_LINK}"
        )
    else:
        msg = (
            "╭━━━━━━━━━━━━━━━━━━━━✪\n"
            "│  🆓 𝐅𝐑𝐄𝐄 𝐔𝐒𝐄𝐑 𝐃𝐀𝐒𝐇𝐁𝐎𝐀𝐑𝐃\n"
            "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 👤 𝐀𝐂𝐂𝐎𝐔𝐍𝐓 𝐈𝐍𝐅𝐎 ✦ ⟯\n"
            f"│  👤 𝐔𝐬𝐞𝐫   : <b>{safe_name}</b>\n"
            "│  💎 𝐏𝐥𝐚𝐧   : 𝐅𝐫𝐞𝐞\n"
            "│  🟢 𝐒𝐭𝐚𝐭𝐮𝐬 : 𝐀𝐜𝐭𝐢𝐯𝐞\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 📉 𝐋𝐈𝐌𝐈𝐓𝐀𝐓𝐈𝐎𝐍𝐒 ✦ ⟯\n"
            "│  👍 𝐋𝐢𝐤𝐞𝐬  : 𝟐 / 𝐃𝐚𝐲\n"
            "│  👁️ 𝐕𝐢𝐬𝐢𝐭𝐬 : 𝐔𝐧𝐥𝐢𝐦𝐢𝐭𝐞𝐝\n"
            "│  ⏳ 𝐂𝐨𝐨𝐥𝐝𝐨𝐰𝐧 : 𝟐𝟒 𝐇𝐨𝐮𝐫𝐬\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 💎 𝐔𝐏𝐆𝐑𝐀𝐃𝐄 𝐁𝐄𝐍𝐄𝐅𝐈𝐓𝐒 ✦ ⟯\n"
            "│  ✓ 𝐔𝐧𝐥𝐢𝐦𝐢𝐭𝐞𝐝 𝐋𝐢𝐤𝐞𝐬\n"
            "│  ✓ 𝐍𝐨 𝐃𝐚𝐢𝐥𝐲 𝐋𝐢𝐦𝐢𝐭\n"
            "│  ✓ 𝐅𝐚𝐬𝐭𝐞𝐫 𝐃𝐞𝐥𝐢𝐯𝐞𝐫𝐲\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            f"👑 𝐔𝐩𝐠𝐫𝐚𝐝𝐞 𝐍𝐨𝐰 • {OWNER_LINK}"
        )
    await update.message.reply_text(msg, parse_mode="HTML")

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 𝐀𝐝𝐦𝐢𝐧 𝐎𝐧𝐥𝐲")
    try:
        if len(context.args) != 2:
            return await update.message.reply_text("❌ 𝐔𝐬𝐚𝐠𝐞: /adduser 𝐔𝐒𝐄𝐑_𝐈𝐃 𝐃𝐚𝐲𝐬")
        uid = context.args[0]
        days = int(context.args[1])
        expiry = datetime.now() + timedelta(days=days)
        with DATA_LOCK:
            get_data()["premium"][uid] = expiry.isoformat()
        msg = (
            "╭━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "│   👑 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐀𝐂𝐓𝐈𝐕𝐀𝐓𝐄𝐃   │\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "╭━⟮ 👤 𝐔𝐒𝐄𝐑 𝐈𝐍𝐅𝐎 ⟯━╮\n"
            f"│  🆔 𝐈𝐃   : <code>{uid}</code>\n"
            f"│  💎 𝐏𝐥𝐚𝐧 : <b>𝐏𝐑𝐄𝐌𝐈𝐔𝐌</b>\n"
            f"│  ⏳ 𝐃𝐚𝐲𝐬 : <b>{days}</b>\n"
            f"│  📅 𝐄𝐱𝐩  : <b>{expiry.strftime('%d-%b-%Y')}</b>\n"
            "╰━━━━━━━━━━━━━━╯\n\n"
            f"🔥 𝐌𝐚𝐧𝐚𝐠𝐞𝐝 𝐛𝐲 {OWNER_LINK}"
        )
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        print("Add User Error:", e)
        await update.message.reply_text("❌ 𝐄𝐫𝐫𝐨𝐫 𝐰𝐡𝐢𝐥𝐞 𝐚𝐜𝐭𝐢𝐯𝐚𝐭𝐢𝐧𝐠 𝐩𝐫𝐞𝐦𝐢𝐮𝐦.")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 𝐀𝐝𝐦𝐢𝐧 𝐎𝐧𝐥𝐲")
    try:
        if len(context.args) != 1:
            return await update.message.reply_text("❌ 𝐔𝐬𝐚𝐠𝐞: /removeuser 𝐔𝐒𝐄𝐑_𝐈𝐃")
        uid = context.args[0]
        with DATA_LOCK:
            if uid in get_data()["premium"]:
                del get_data()["premium"][uid]
            else:
                return await update.message.reply_text("❌ 𝐔𝐬𝐞𝐫 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝 𝐢𝐧 𝐩𝐫𝐞𝐦𝐢𝐮𝐦 𝐥𝐢𝐬𝐭.")
        msg = (
            "╭━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "│   ❌ 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐑𝐄𝐌𝐎𝐕𝐄𝐃   │\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "╭━⟮ 👤 𝐔𝐒𝐄𝐑 𝐈𝐍𝐅𝐎 ⟯━╮\n"
            f"│  🆔 𝐈𝐃     : <code>{uid}</code>\n"
            f"│  💎 𝐏𝐥𝐚𝐧   : 𝐏𝐑𝐄𝐌𝐈𝐔𝐌\n"
            f"│  ⛔ 𝐒𝐭𝐚𝐭𝐮𝐬 : 𝐈𝐍𝐀𝐂𝐓𝐈𝐕𝐄\n"
            "╰━━━━━━━━━━━━━━╯\n\n"
            f"⚠️ 𝐀𝐜𝐜𝐞𝐬𝐬 𝐑𝐞𝐯𝐨𝐤𝐞𝐝\n"
            f"🔥 𝐌𝐚𝐧𝐚𝐠𝐞𝐝 𝐛𝐲 {OWNER_LINK}"
        )
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        print("Remove User Error:", e)
        await update.message.reply_text("❌ 𝐄𝐫𝐫𝐨𝐫 𝐰𝐡𝐢𝐥𝐞 𝐫𝐞𝐦𝐨𝐯𝐢𝐧𝐠 𝐩𝐫𝐞𝐦𝐢𝐮𝐦.")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        return await update.message.reply_text("❌ 𝐔𝐬𝐚𝐠𝐞: /broadcast 𝐘𝐨𝐮𝐫 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐡𝐞𝐫𝐞")
    msg_text = " ".join(context.args)
    total = len(get_data().get("all_users", []))
    success = 0
    failed = 0
    for uid in get_data().get("all_users", []):
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=(
                    "╭━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                    "│        📢 𝐁𝐑𝐎𝐀𝐃𝐂𝐀𝐒𝐓        │\n"
                    "╰━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                    f"{msg_text}"
                )
            )
            success += 1
        except:
            failed += 1
    report_msg = (
        "╭━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "│     📊 𝐁𝐑𝐎𝐀𝐃𝐂𝐀𝐒𝐓 𝐑𝐄𝐏𝐎𝐑𝐓     │\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        "╭━⟮ 📈 𝐒𝐓𝐀𝐓𝐒 ⟯━╮\n"
        f"│  👥 𝐓𝐨𝐭𝐚𝐥 𝐔𝐬𝐞𝐫𝐬 : <b>{total}</b>\n"
        f"│  ✅ 𝐒𝐞𝐧𝐭        : <b>{success}</b>\n"
        f"│  ❌ 𝐅𝐚𝐢𝐥𝐞𝐝      : <b>{failed}</b>\n"
        "╰━━━━━━━━━━━━━━╯"
    )
    await update.message.reply_text(report_msg, parse_mode="HTML")

async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        return await update.message.reply_text("❌ 𝐔𝐬𝐚𝐠𝐞: /maintenance 𝐨𝐧/𝐨𝐟𝐟")
    mode = context.args[0].lower() == "on"
    with DATA_LOCK:
        get_data()["maintenance"] = mode
    await update.message.reply_text(f"⚙️ 𝐌𝐚𝐢𝐧𝐭𝐞𝐧𝐚𝐧𝐜𝐞: <b>{'𝐎𝐍' if mode else '𝐎𝐅𝐅'}</b>", parse_mode="HTML")

async def post_init(application: Application):
    application.job_queue.run_repeating(
        auto_like_job,
        interval=60,
        first=10
    )

if __name__ == '__main__':
    load_data_initial()
    threading.Thread(target=background_db_saver, daemon=True).start()

    request = HTTPXRequest(connect_timeout=60, read_timeout=60, write_timeout=60, pool_timeout=60)
    app = ApplicationBuilder().token(BOT_TOKEN).request(request).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("like", like_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("myplan", myplan_command))
    app.add_handler(CommandHandler("adduser", add_user))
    app.add_handler(CommandHandler("removeuser", remove_user))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("maintenance", maintenance_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("autolike", autolike_command))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("allliststatus", allliststatus_command))
    app.add_handler(CommandHandler("mylikes", mylikes_command))
    app.add_handler(CommandHandler("cooldown", cooldown_command))
    app.add_handler(CommandHandler("uidinfo", uidinfo_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="show_help"))

    print("""
🚀━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ 𝐊𝐀𝐌𝐎𝐃 𝐁𝐎𝐓 𝐄𝐍𝐆𝐈𝐍𝐄 𝐒𝐓𝐀𝐑𝐓𝐄𝐃
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mode        : LIKE API
Token System: REMOVED
Auto Like   : 4:00 AM IST
Server      : ONLINE 🟢
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    app.run_polling()