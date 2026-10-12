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

# Files
DATA_FILE = "users.json"

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ==============================================================================
#             SAFE DATABASE SYSTEM (NO DATA LOSS FIX)
# ==============================================================================
MEM_DATA = {
    "cooldowns": {},
    "premium": {},
    "all_users": [],
    "maintenance": False,
    "usernames": {},
    "autolike": [],
    "admins": {}   # 🔥 Added Admin System
}
DATA_LOCK = threading.Lock()

def load_data_initial():
    global MEM_DATA
    # Check if file exists and is NOT empty
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        print("⚠️ Users file missing or empty. Creating new database.")
        save_data_force()
        return

    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            # Fix Premium Format if needed
            if isinstance(data.get("premium"), list):
                new_prem = {}
                expiry = (datetime.now() + timedelta(days=30)).isoformat()
                for uid in data["premium"]: new_prem[str(uid)] = expiry
                data["premium"] = new_prem
            
            # Load data into RAM
            for key in MEM_DATA:
                if key in data: MEM_DATA[key] = data[key]
            print(f"✅ Database Loaded: {len(MEM_DATA['all_users'])} Users")
            
    except json.JSONDecodeError:
        print("❌ Database Corrupted! Backup created as users_backup.json")
        os.rename(DATA_FILE, "users_backup.json")
        save_data_force()
    except Exception as e: 
        print(f"DB Error: {e}")

def save_data_force():
    """Saves data safely using a temporary file to prevent 0 Byte corruption"""
    with DATA_LOCK:
        temp_file = f"{DATA_FILE}.tmp"
        try:
            with open(temp_file, "w") as f: 
                json.dump(MEM_DATA, f, indent=4)
            
            # Atomic replacement (Safe Save)
            os.replace(temp_file, DATA_FILE)
        except Exception as e:
            print(f"❌ Save Failed: {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

def background_db_saver():
    while True:
        time.sleep(30)
        try: save_data_force()
        except: pass


def record_user(user):
    uid = user.id
    username = user.username.lower() if user.username else None
    with DATA_LOCK:
        if uid not in MEM_DATA["all_users"]: MEM_DATA["all_users"].append(uid)
        if username: MEM_DATA["usernames"][username] = uid

def get_data(): return MEM_DATA

def get_india_time():
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

# ==============================================================================
#             PART 3: NETWORK REQUESTS
# ==============================================================================
# ================= LIKE API CONFIG =================
LIKE_API_URL = "https://like-api-by-kamod.onrender.com/like"

def call_like_api(uid, region="ind"):
    """Call the configured like API and return its JSON/text response."""
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
    """Read the API's documented fields and normalize the Telegram report."""
    if not isinstance(data, dict):
        return False, 0, before, before, "Unexpected API response", "Unknown"

    # API example: status=2, LikesGivenByAPI, LikesbeforeCommand,
    # LikesafterCommand, PlayerNickname, UID.
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
    except (TypeError, ValueError):
        added = 0
    try:
        reported_before = int(reported_before if reported_before is not None else before)
    except (TypeError, ValueError):
        reported_before = before
    try:
        after = int(after) if after is not None else reported_before + added
    except (TypeError, ValueError):
        after = reported_before + added

    message = str(data.get("message", data.get("msg", data.get("error", ""))))
    # Don't treat 0 added likes as a failed API call if status says success.
    if not success_flag and (added > 0 or after > reported_before):
        success_flag = True
    return success_flag, added, reported_before, after, message, nickname

async def process_like_task(chat_id, uid, region, context, msg_id, user_id, is_premium, today_used):

    if region.lower() != "ind":
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=("╔════════════════════╗\n"
                      "      🚫 SERVER ERROR\n"
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
                text=("⚡ <b>KAMOD PREMIUM CONSOLE</b> ⚡\n"
                      "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                      f"👤 UID : <code>{html.escape(str(uid))}</code>\n"
                      f"<code>{bar} {percent}%</code>\n\n"
                      "🚀 Processing..."),
                parse_mode="HTML"
            )
            await asyncio.sleep(0.25)
    except Exception:
        pass

    try:
        # API call runs in a worker thread so the Telegram event loop stays responsive.
        api_data = await asyncio.to_thread(call_like_api, uid, region)
        success_flag, added, before, after, api_message, player_name = api_result_values(api_data, 0)
    except Exception as e:
        success_flag, added, before, after, player_name = False, 0, 0, 0, "Unknown"
        api_message = str(e)

    keyboard = [[
        InlineKeyboardButton("👑 OWNER", url="https://t.me/kamod90"),
        InlineKeyboardButton("📢 MAIN CHANNEL", url="https://t.me/KAMOD_CODEX"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if not success_flag:
        msg_text = (
            "╭━━━━━━━━━━━━━━━━━━━━✪\n"
            "│  ❌ LIKE DELIVERY FAILED\n"
            "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 👤 PLAYER INFO ✦ ⟯\n"
            f"│  Name   : {html.escape(player_name)}\n"
            f"│  UID    : {html.escape(str(uid))}\n"
            f"│  Region : {html.escape(str(region).upper())}\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ ❤️ LIKE DETAILS ✦ ⟯\n"
            f"│  Before : {before}\n"
            f"│  After  : {after}\n"
            f"│  Added  : +{added}\n"
            "╰━━━━━━━━━━━━━━━━━━✪"
        )
        if api_message:
            msg_text += "\n\nAPI: " + html.escape(api_message[:250])
    else:
        if not is_premium:
            with DATA_LOCK:
                get_data()["cooldowns"].setdefault(str(user_id), []).append({
                    "uid": str(uid),
                    "time": get_india_time().isoformat()
                })
        msg_text = (
            "╭━━━━━━━━━━━━━━━━━━━━✪\n"
            "│  ✅ LIKE SENT SUCCESSFULLY\n"
            "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 👤 PLAYER INFO ✦ ⟯\n"
            f"│  Name   : {html.escape(player_name)}\n"
            f"│  UID    : {html.escape(str(uid))}\n"
            f"│  Region : {html.escape(str(region).upper())}\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ ❤️ LIKE DETAILS ✦ ⟯\n"
            f"│  Before : {before}\n"
            f"│  After  : {after}\n"
            f"│  Added  : +{added}\n"
            "╰━━━━━━━━━━━━━━━━━━✪"
        )

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id, text=msg_text,
            parse_mode="HTML", reply_markup=reply_markup
        )
    except Exception:
        pass

# --- AUTO LIKE LOOP ---
async def auto_like_job(context: ContextTypes.DEFAULT_TYPE):
    app = context.application
    now = get_india_time()
    current_time_str = now.strftime("%I:%M %p")
    today_date = now.strftime("%Y-%m-%d")

    tasks_to_run = []

    with DATA_LOCK:
        for task in get_data().get("autolike", []):
            if (
                task["time"] == current_time_str
                and task["last_run"] != today_date
                and task["days"] > 0
            ):
                tasks_to_run.append(task)

    for task in tasks_to_run:
        await process_auto_like_task(app, task, today_date)
        
def is_admin(user_id):

    # Owner always admin
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
            if task["days"] <= 0:
                try:
                    get_data()["autolike"].remove(task)
                except ValueError:
                    pass

        now = get_india_time()
        status_title = "🤖 AUTO LIKE SUCCESSFUL" if success_flag else "🤖 AUTO LIKE FAILED"
        msg = (
            "╭━━━━━━━━━━━━━━━━━━━━✪\n"
            f"│ {status_title}\n"
            "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 👤 PLAYER INFO ✦ ⟯\n"
            f"│  Name   : {html.escape(player_name)}\n"
            f"│  UID    : {html.escape(str(task['uid']))}\n"
            f"│  Region : {html.escape(str(task['region']).upper())}\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ ❤️ DELIVERY REPORT ✦ ⟯\n"
            f"│  Before : {before}\n"
            f"│  Added  : +{added}\n"
            f"│  Total  : {after}\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            f"│  Remaining Days : {task['days']}\n"
            f"│  Time           : {now.strftime('%H:%M:%S')}\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            f"💎 Buy Auto Like : {OWNER_LINK}"
        )
        if api_message and not success_flag:
            msg += "\n\nAPI: " + html.escape(api_message[:250])
        try:
            await app.bot.send_message(chat_id=GROUP_LINK, text=msg, parse_mode="HTML")
        except Exception:
            pass
    except Exception as e:
        print("AutoLike API Error:", e)

#             PART 5: COMMAND HANDLERS
# ==============================================================================

async def check_subscription(user_id, context):
    if user_id == ADMIN_ID: return True
    not_joined = []
    for channel in MUST_JOIN_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in [ChatMember.LEFT, ChatMember.BANNED, ChatMember.RESTRICTED]:
                not_joined.append(channel)
        except: pass 
    return len(not_joined) == 0

# [REQUEST 3] Force Join Update - Premium Poster & Verify Logic
async def force_join_alert(update, context):
    keyboard = [
        [InlineKeyboardButton("📢 JOIN CHANNEL NOW", url=f"https://t.me/{CHANNEL_LINK.replace('@','')}")],
        [InlineKeyboardButton("Verify & Try Again", callback_data="check_join")]
    ]

    msg = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  🚨 ACCESS REQUIRED\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "Join official channel\n"
        "before using this bot.\n\n"
        "╭━⟮ ✦ STEPS ✦ ⟯\n"
        "│  1. Join Channel\n"
        "│  2. Click Verify\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        f"Official Support : {OWNER_LINK}"
    )

    if update.callback_query:
        await update.callback_query.message.edit_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    # Send message with premium formatting
    if update.callback_query:
        await update.callback_query.message.edit_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    else:
        await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user if update.effective_user else update.callback_query.from_user
    record_user(user)
    if not await check_subscription(user.id, context): return await force_join_alert(update, context)
    
    safe_name = html.escape(user.first_name)
    poster = (
        "⚡ 𝗞𝗔𝗠𝗢𝗗 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗖𝗢𝗡𝗦𝗢𝗟𝗘 ⚡\n"
        " 𝘃 𝟯.𝟬 | 𝗦𝘁𝗮𝘁𝘂𝘀: 𝗢𝗻𝗹𝗶𝗻𝗲 🟢\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 𝗛𝗲𝘆 <b>{safe_name}</b>!\n"
        "🚀 <i>Welcome to the Ultimate FF Tool.</i>\n\n"
        "<b>💠 Main Features:</b>\n"
        "👍 <code>Auto Like</code>  |  👁️ <code>Auto Visit</code>\n"
        "📊 <code>Rank Push</code>  |  🛡️ <code>Anti-Ban</code>\n\n"
        "👇 <b>Click Command List to Begin:</b>"
    )
    kb = [[InlineKeyboardButton("📜 Command List", callback_data="show_help")], [InlineKeyboardButton("🆘 Support", url=f"https://t.me/{OWNER_LINK.replace('@', '')}")]]
    
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
        await query.answer("✅ Access Granted!")
        try: 
            await query.message.delete() # [REQUEST 3] Delete warning message
        except: pass
        # [REQUEST 3] Show Help Menu immediately after verify
        await help_command(update, context) 
    else: 
        await query.answer("❌ Join nahi kiya!", show_alert=True)

# [REQUEST 4] Updated Help Menu & Added Info Command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ensure subscription (double check if called directly)
    if not await check_subscription(update.effective_user.id, context): return await force_join_alert(update, context)
    
    help_text = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  📜 COMMAND CENTER\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 👤 USER COMMANDS ✦ ⟯\n"
        "│  ❤️  /like IND UID\n"
        "│  👁️  /visit IND UID\n"
        "│  💎  /myplan\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 🛡️ ADMIN COMMANDS ✦ ⟯\n"
        "│  ➕  /adduser ID Days\n"
        "│  ➖  /removeuser ID\n"
        "│  👑  /addadmin ID Days\n"
        "│  ❌  /removeadmin ID\n"
        "│  🤖  /autolike IND UID Time Days\n"
        "│  📊  /status\n"
        "│  📢  /broadcast Message\n"
        "│  ⚙️  /maintenance on/off\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        f"Owner : {OWNER_LINK}"
    )
    kb = [[InlineKeyboardButton("💬 CONTACT SUPPORT", url=f"https://t.me/{OWNER_LINK.replace('@', '')}")]]
    
    if update.callback_query: 
        await update.callback_query.message.edit_text(help_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    else: 
        await context.bot.send_message(update.effective_chat.id, text=help_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def like_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    record_user(user)

    # 🔧 Maintenance Mode
    if get_data().get("maintenance") and user.id != ADMIN_ID:
        return await update.message.reply_text(
            "🚧 <b>Maintenance Mode!</b>",
            parse_mode="HTML"
        )

    if not await check_subscription(user.id, context):
        return await force_join_alert(update, context)

    # ======================================================
    # ❌ PRIVATE CHAT BLOCK (BOX STYLE + BUTTON)
    # ======================================================
    if update.effective_chat.type == "private" and user.id != ADMIN_ID:

        group_only_msg = (
            "╭━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "│   ❌ COMMAND NOT AVAILABLE   │\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"

            "╭━⟮ ⚠️ ACCESS RESTRICTED ⟯━╮\n"
            "│  This command works only\n"
            "│  inside the official group.\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"

            "👥 Join Official Group Below"
        )

        keyboard = [[
            InlineKeyboardButton(
    "👥 JOIN OFFICIAL GROUP",
    url=f"https://t.me/{GROUP_LINK.replace('@','')}"
)
        ]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        return await update.message.reply_text(
            group_only_msg,
            reply_markup=reply_markup
        )

    # ======================================================
    # ❌ USAGE CHECK
    # ======================================================
    if len(context.args) != 2:
        return await update.message.reply_text(
            "❌ <b>Usage:</b> <code>/like IND 12345678</code>",
            parse_mode="HTML"
        )

    data = get_data()

    # 👑 PREMIUM CHECK
    is_premium = str(user.id) in data["premium"] or user.id == ADMIN_ID

    if is_premium and str(user.id) in data["premium"]:
        try:
            if datetime.fromisoformat(data["premium"][str(user.id)]) < datetime.now():
                is_premium = False
        except:
            is_premium = False

    today_used = 0

    # ======================================================
    # FREE USER COOLDOWN SYSTEM
    # ======================================================
    if not is_premium:

        history = data["cooldowns"].get(str(user.id), [])
        valid = []

        for e in history:
            try:
                event_time = datetime.fromisoformat(e["time"])
                if get_india_time() - event_time < timedelta(hours=24):
                    valid.append(e)
            except:
                pass

        data["cooldowns"][str(user.id)] = valid
        today_used = len(valid)

        # 🔁 UID COOLDOWN CHECK
        for entry in valid:
            if entry["uid"] == context.args[1]:

                last_used = datetime.fromisoformat(entry["time"])
                unlock_at = last_used + timedelta(hours=24)
                remaining = unlock_at - get_india_time()

                if remaining.total_seconds() > 0:

                    hours, remainder = divmod(
                        int(remaining.total_seconds()), 3600
                    )
                    minutes, _ = divmod(remainder, 60)

                    cooldown_msg = (
                        "╭━━━━━━━━━━━━━━━━━╮\n"
                        "│ ⛔  COOLDOWN ACTIVE │\n"
                        "╰━━━━━━━━━━━━━━━━━╯\n\n"

                        "╭━⟮ ⚠️ STATUS ⟯━╮\n"
                        "│  UID already received\n"
                        "│  likes today.\n"
                        "╰━━━━━━━━━━━━━━╯\n\n"

                        "╭━⟮ ⏳ TIME LEFT ⟯━╮\n"
                        f"│  {hours}h {minutes}m remaining\n"
                        "╰━━━━━━━━━━━━━━╯"
                    )

                    return await update.message.reply_text(cooldown_msg)

        # ❌ DAILY LIMIT CHECK
        if len(valid) >= 2:

            limit_msg = (
                "╭━━━━━━━━━━━━━━━━━━╮\n"
                "│  DAILY LIMIT REACHED   │\n"
                "╰━━━━━━━━━━━━━━━━━━╯\n\n"

                "╭━⟮ 📊 LIMIT INFO ⟯━╮\n"
                "│  Free users can send\n"
                "│  only 2 uid likes per day.\n"
                "╰━━━━━━━━━━━━━━╯\n\n"

                f"👑 Upgrade to PREMIUM\n"
                f"📩 {OWNER_LINK}"
            )

            return await update.message.reply_text(limit_msg)

    # API mode: no local token files are needed.

    # ======================================================
    # START PROCESS
    # ======================================================
    msg = await update.message.reply_text(
        "❤️ <b>Sending Likes...</b>",
        parse_mode="HTML"
    )

    asyncio.create_task(
        process_like_task(
            update.effective_chat.id,
            context.args[1],
            context.args[0].upper(),
            context,
            msg.message_id,
            user.id,
            is_premium,
            today_used
        )
    )

async def autolike_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # ✅ Allow Owner + Added Admins
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("🚫 Admin Only")

    if len(context.args) != 4:
        return await update.message.reply_text(
            "❌ Usage: /autolike IND <UID> 10:30PM 5",
            parse_mode="HTML"
        )

    region = context.args[0].upper()
    uid = context.args[1]
    time_str = context.args[2]

    try:
        days = int(context.args[3])
    except:
        return await update.message.reply_text("❌ Days must be number")

    # ✅ Validate Time Format
    try:
        formatted_time = datetime.strptime(time_str, "%I:%M%p").strftime("%I:%M %p")
    except:
        return await update.message.reply_text(
            "❌ Invalid Time Format!\nExample: 10:30PM",
            parse_mode="HTML"
        )

    new_task = {
        "region": region,
        "uid": uid,
        "time": formatted_time,
        "days": days,
        "last_run": ""
    }

    with DATA_LOCK:
        get_data()["autolike"].append(new_task)

    now = get_india_time()
    start_date = now.strftime("%d-%b-%Y")
    expiry_date = (now + timedelta(days=days)).strftime("%d-%b-%Y")

    msg = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  🤖 AUTO LIKE ACTIVATED\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"

        "╭━⟮ ✦ 👤 PLAYER DETAILS ✦ ⟯\n"
        f"│  UID     : {uid}\n"
        f"│  Region  : {region}\n"
        f"│  Mode    : API\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"

        "╭━⟮ ✦ ⏰ SCHEDULE INFO ✦ ⟯\n"
        f"│  Start Date  : {start_date}\n"
        f"│  Expiry Date : {expiry_date}\n"
        f"│  Daily Time  : {formatted_time}\n"
        f"│  Total Days  : {days}\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"

        "╭━⟮ ✦ 🚀 STATUS ✦ ⟯\n"
        "│  Auto Like Engine : ACTIVE 🟢\n"
        "│  Execution Mode   : Automatic\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"

        f"💎 Managed by {OWNER_LINK}"
    )

    await update.message.reply_text(msg, parse_mode="HTML")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("🚫 Admin Only")

    data = get_data()
    msg_text = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  📊 SYSTEM MONITOR\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
        "╭━⟮ ✦ 👥 USERS ✦ ⟯\n"
        f"│  Total    : {len(data['all_users'])}\n"
        f"│  Premium  : {len(data['premium'])}\n"
        f"│  Admins   : {len(data.get('admins', {}))}\n"
        f"│  Autolike : {len(data['autolike'])}\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"
        "⚡ Like System : API\n"
        "⚡ Bot Status  : Online 🟢\n"
        f"👑 Owner : {OWNER_LINK}"
    )
    await update.message.reply_text(msg_text, parse_mode="HTML")

async def allliststatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("🚫 Admin Only")

    data = get_data()

    with DATA_LOCK:
        autolike_list = data.get("autolike", [])
        premium_users = data.get("premium", {})
        admin_users = data.get("admins", {})

    # AutoLike List
    if autolike_list:
        auto_text = "\n".join(
            [f"🎯 UID: {t['uid']} | 🌍 {t['region']}" for t in autolike_list]
        )
    else:
        auto_text = "No AutoLike Active"

    # Premium List
    if premium_users:
        premium_text = "\n".join([f"👑 {uid}" for uid in premium_users.keys()])
    else:
        premium_text = "No Premium Users"

    # Admin List
    if admin_users:
        admin_text = "\n".join([f"🛡 {uid}" for uid in admin_users.keys()])
    else:
        admin_text = "No Admins"

    msg = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  📋 ALL LIST STATUS\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"

        "📌 AUTO LIKE LIST:\n"
        f"{auto_text}\n\n"

        "👑 PREMIUM USERS:\n"
        f"{premium_text}\n\n"

        "🛡 ADMIN USERS:\n"
        f"{admin_text}"
    )

    await update.message.reply_text(msg)
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # 🔒 Only Owner Can Add Admin
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 Only Owner Can Use This Command")

    if len(context.args) != 2:
        return await update.message.reply_text(
            "Usage: /addadmin USER_ID Days",
            parse_mode="HTML"
        )

    user_id = context.args[0]

    try:
        days = int(context.args[1])
    except:
        return await update.message.reply_text("❌ Days must be number")

    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    expiry_fmt = (datetime.now() + timedelta(days=days)).strftime("%d-%b-%Y")

    with DATA_LOCK:
        get_data()["admins"][str(user_id)] = expiry

    msg = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  👑 ADMIN ACCESS GRANTED\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"

        "╭━⟮ ✦ 👤 ADMIN DETAILS ✦ ⟯\n"
        f"│  User ID     : {user_id}\n"
        f"│  Role        : Administrator\n"
        f"│  Valid For   : {days} Days\n"
        f"│  Expiry Date : {expiry_fmt}\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"

        "╭━⟮ ✦ 🔐 PERMISSIONS ✦ ⟯\n"
        "│  ✓ Auto Like Control\n"
        "│  ✓ Status Access\n"
        "│  ✓ Broadcast Access\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"

        f"👑 Granted By : {OWNER_LINK}"
    )

    await update.message.reply_text(msg, parse_mode="HTML")
    

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # 🔒 Only Owner Can Remove Admin
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 Only Owner Can Use This Command")

    if len(context.args) != 1:
        return await update.message.reply_text(
            "Usage: /removeadmin USER_ID",
            parse_mode="HTML"
        )

    user_id = context.args[0]

    with DATA_LOCK:
        if str(user_id) not in get_data()["admins"]:
            return await update.message.reply_text("❌ User Not Admin")

        del get_data()["admins"][str(user_id)]

    msg = (
        "╭━━━━━━━━━━━━━━━━━━━━✪\n"
        "│  ❌ ADMIN ACCESS REVOKED\n"
        "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"

        "╭━⟮ ✦ 👤 ADMIN DETAILS ✦ ⟯\n"
        f"│  User ID : {user_id}\n"
        f"│  Role    : Administrator\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"

        "╭━⟮ ✦ ⚠️ STATUS UPDATE ✦ ⟯\n"
        "│  Access : Removed\n"
        "│  Panel  : Disabled\n"
        "╰━━━━━━━━━━━━━━━━━━✪\n\n"

        f"🔒 Removed By : {OWNER_LINK}"
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
            "│  💎 VIP DASHBOARD\n"
            "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 👤 ACCOUNT INFO ✦ ⟯\n"
            f"│  User   : {safe_name}\n"
            "│  Plan   : Premium\n"
            f"│  Expiry : {expiry_fmt}\n"
            f"│  Days   : {days_left}\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 🚀 BENEFITS ✦ ⟯\n"
            "│  ✓ Unlimited Likes\n"
            "│  ✓ No Cooldown\n"
            "│  ✓ Priority Access\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            f"Elite Member • {OWNER_LINK}"
        )

    else:
        msg = (
            "╭━━━━━━━━━━━━━━━━━━━━✪\n"
            "│  🆓 FREE USER DASHBOARD\n"
            "╰━━━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 👤 ACCOUNT INFO ✦ ⟯\n"
            f"│  User   : {safe_name}\n"
            "│  Plan   : Free\n"
            "│  Status : Active\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 📉 LIMITATIONS ✦ ⟯\n"
            "│  👍 Likes  : 2 / Day\n"
            "│  👁️ Visits : Unlimited\n"
            "│  ⏳ Cooldown : 24 Hours\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            "╭━⟮ ✦ 💎 UPGRADE BENEFITS ✦ ⟯\n"
            "│  ✓ Unlimited Likes\n"
            "│  ✓ No Daily Limit\n"
            "│  ✓ Faster Delivery\n"
            "╰━━━━━━━━━━━━━━━━━━✪\n\n"
            f"Upgrade Now • {OWNER_LINK}"
        )

    await update.message.reply_text(msg, parse_mode="HTML")

from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta

# =====================================================
# 👑 ADD PREMIUM USER
# =====================================================
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 Admin Only")

    try:
        if len(context.args) != 2:
            return await update.message.reply_text(
                "Usage: /addpremium USER_ID Days"
            )

        uid = context.args[0]
        days = int(context.args[1])

        expiry = datetime.now() + timedelta(days=days)

        with DATA_LOCK:
            get_data()["premium"][uid] = expiry.isoformat()

        msg = (
            "╭━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "│   👑 PREMIUM ACTIVATED   │\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"

            "╭━⟮ 👤 USER INFO ⟯━╮\n"
            f"│  🆔 ID   : {uid}\n"
            f"│  💎 Plan : PREMIUM\n"
            f"│  ⏳ Days : {days}\n"
            f"│  📅 Exp  : {expiry.strftime('%d-%b-%Y')}\n"
            "╰━━━━━━━━━━━━━━╯\n\n"

            f"🔥 Managed by {OWNER_LINK}"
        )

        await update.message.reply_text(msg)

    except Exception as e:
        print("Add User Error:", e)
        await update.message.reply_text("❌ Error while activating premium.")


# =====================================================
# ❌ REMOVE PREMIUM USER
# =====================================================
async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 Admin Only")

    try:
        if len(context.args) != 1:
            return await update.message.reply_text(
                "Usage: /removepremium USER_ID"
            )

        uid = context.args[0]

        with DATA_LOCK:
            if uid in get_data()["premium"]:
                del get_data()["premium"][uid]
            else:
                return await update.message.reply_text(
                    "❌ User not found in premium list."
                )

        msg = (
            "╭━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "│   ❌ PREMIUM REMOVED   │\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"

            "╭━⟮ 👤 USER INFO ⟯━╮\n"
            f"│  🆔 ID     : {uid}\n"
            f"│  💎 Plan   : PREMIUM\n"
            f"│  ⛔ Status : INACTIVE\n"
            "╰━━━━━━━━━━━━━━╯\n\n"

            f"⚠️ Access Revoked\n"
            f"🔥 Managed by {OWNER_LINK}"
        )

        await update.message.reply_text(msg)

    except Exception as e:
        print("Remove User Error:", e)
        await update.message.reply_text("❌ Error while removing premium.")


# =====================================================
# 📢 BROADCAST MESSAGE
# =====================================================
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        return await update.message.reply_text(
            "Usage: /broadcast Your message here"
        )

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
                    "│        📢 BROADCAST        │\n"
                    "╰━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                    f"{msg_text}"
                )
            )
            success += 1
        except:
            failed += 1

    report_msg = (
        "╭━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "│     📊 BROADCAST REPORT     │\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"

        "╭━⟮ 📈 STATS ⟯━╮\n"
        f"│  👥 Total Users : {total}\n"
        f"│  ✅ Sent        : {success}\n"
        f"│  ❌ Failed      : {failed}\n"
        "╰━━━━━━━━━━━━━━╯"
    )

    await update.message.reply_text(report_msg)

async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    mode = context.args[0].lower() == "on"
    with DATA_LOCK: get_data()["maintenance"] = mode
    await update.message.reply_text(f"Maintenance: {mode}")

# 🔥 STARTUP LOGIC
async def post_init(application: Application):
    application.job_queue.run_repeating(
        auto_like_job,
        interval=60,
        first=10
    )

if __name__ == '__main__':
    load_data_initial()
    
    threading.Thread(target=background_db_saver, daemon=True).start()

    # 🔥 FIX: HTTPX Request - High timeouts and limits for Multi-User
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
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="show_help"))

    print("""
🚀━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ KAMOD BOT ENGINE STARTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Mode        : LIKE API
Token System: REMOVED
Server      : ONLINE 🟢
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    # Python 3.14 compatibility: python-telegram-bot expects a current event loop.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    app.run_polling()