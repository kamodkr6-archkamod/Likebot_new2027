import telegram
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import Update, MessageEntity
import requests
import json
import os
import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError
import re
from typing import Dict, List, Any, Optional
from zoneinfo import ZoneInfo
import tempfile
import shutil
import random
import string
import emoji

# --- Configuration ---
BOT_TOKEN = "8422322370:AAEZoV2YfQs-E0IYvrMl0zymrgOvR_UEays"
DATA_FILE = "bot_data.json"
LOG_FILE = "bot.log"
OWNER_ID = 8138834246
DAILY_LIKE_TIME = "05:00"
IST = ZoneInfo("Asia/Kolkata")

# --- PREMIUM EMOJI CONFIGURATION ---
# Sabhi responses mein premium emoji use honge
CUSTOM_EMOJIS = {
    "welcome": ("⭐", "6336646834139700626"),
    "success": ("✅", "6336861449360514102"),
    "error": ("❌", "6337033209397649451"),
    "broadcast": ("📢", "6336698133229082903"),
    "status": ("📊", "6336674562448563935"),
    "bot_active": ("🚀", "6336674562448563935"),
    "like": ("❤️", "6336861449360514102"),
    "user": ("👤", "6336674562448563935"),
    "uid": ("🔢", "6336646834139700626"),
    "region": ("🌍", "6336674562448563935"),
    "level": ("📊", "6336674562448563935"),
    "time": ("⏰", "6336674562448563935"),
    "days": ("📅", "6336674562448563935"),
    "pause": ("⏸️", "6336674562448563935"),
    "active": ("✅", "6336861449360514102"),
    "help": ("🤖", "6336674562448563935"),
    "stats": ("📊", "6336674562448563935"),
    "admin": ("👑", "6336674562448563935"),
    "group": ("🏢", "6336674562448563935"),
    "api": ("📈", "6336674562448563935"),
    "info": ("ℹ️", "6336674562448563935"),
    "warning": ("⚠️", "6336674562448563935"),
    "star": ("🌟", "6336646834139700626"),
    "fire": ("🔥", "6336674562448563935"),
    "settings": ("⚙️", "6336674562448563935"),
    "backup": ("📦", "6336674562448563935"),
    "restore": ("♻️", "6336674562448563935"),
    "test": ("🔍", "6336674562448563935"),
    "run": ("▶️", "6336674562448563935"),
    "id": ("🆔", "6336674562448563935"),
    "name": ("📋", "6336674562448563935"),
    "command": ("⚡", "6336674562448563935"),
    "example": ("📝", "6336674562448563935"),
    "result": ("🎯", "6336674562448563935"),
    "date": ("📆", "6336674562448563935"),
    "total": ("🔢", "6336674562448563935"),
    "failed": ("❌", "6337033209397649451"),
    "sent": ("✅", "6336861449360514102"),
    "processing": ("⏳", "6336674562448563935"),
    "completed": ("✅", "6336861449360514102"),
    "active_groups": ("🏢", "6336674562448563935"),
    "users_count": ("👥", "6336674562448563935"),
}

# Premium Emoji IDs List
PREMIUM_EMOJIS = [
    "6100639476441161711", "6102462664288509137", "6100199534351097095",
    "6102926404792360795", "6100409966273764915", "6100430105375415737",
    "6102470558438400435", "6100451820730064687", "6102638599033858630",
    "6100179369479642954", "6100485115316542792", "6102661242101440205",
    "6102592514034770678", "6102475626499808862", "6102863908723236868",
    "6102510630483271620", "6282589525348720171", "6055377380204092112",
    "6055551219005398825", "6055181976371994390", "6055481009175010794",
    "6055484548228062462", "6055202102588742236", "6055450347403484860",
    "6055228576767155521", "6055183995006623379", "6337009415278828759",
    "6336756235546663929", "6334772471757020134", "6336732269629153634",
    "6336833407519038409", "6337048276142924106", "6337018975876030803",
    "6336608132189395373", "6336797785060286399", "6336685231147326793",
    "6336907611669011898", "6336988189550451848", "6337098578799893838",
    "6336808092981796477", "6337020083977592163", "6337112997005107243",
    "6337051755066433311", "6336835907190004485", "6336618976981818626",
    "6336857218817728795", "6336974471424908889", "6337125748763008448",
    "6337098338281725706", "6336962978092425393", "6336633214798404108",
    "6337019139084786234", "6337035356881296575", "6337026908680625329",
    "6336690569791676356", "6337106906741480828", "6337072645787361389",
    "6336720729052027967", "6336670885956557643", "6337113894653271580",
    "6334488003188105980", "6336721798498884548", "6336799284003873851",
    "6337112129421713282", "6336599202952388231", "6336755629956275338",
    "6334702021408465964", "6337109865973948062", "6336708763273142215",
    "6337083451925078342", "6336930400765484501", "6334788126912815244",
    "6337059606266651217", "6336812005697002754", "6336813629194640485",
    "6337085796977221633", "6336663202260065128", "6334324468013341494",
    "6337047855236129713", "6336782885818742144", "6336664645369076808",
    "6336910583786383660", "6336862179504954500", "6336697226990985005",
    "6336772620846899242", "6337033209397649451", "6336861449360514102",
    "6336573617832206335", "6337055242579876765", "6336789422758960593",
    "6336781331040577785", "6336603218746810844", "6337123072998383823",
    "6336894825551371014", "6334681658968513467", "6336799919659031563",
    "6336707603631972035", "6336874467406389346", "6336756411640323933",
    "6336608037700115865", "6336613247495445753", "6336973539417007164",
    "6336931040715612818", "6336653869296132233", "6336836572909938734",
    "6336798231736885254", "6336813951317187443", "6336866435817545002",
    "6336662845777780692", "6336580455420141312", "6336750437340816001",
    "6336677470141422007", "6337078718871117522", "6336931345658289868",
    "6336935322798005307", "6336646834139700626", "6337010179783007229",
    "6336618208182673162", "6336580975111184057", "6336957184181543528",
    "6336991256157101601", "6336655355354815762", "6336795865209904645",
    "6337054177427988529", "6336855354801921798", "6336878444546105899",
    "6336861037043654967", "6336662472115626382", "6337093386184432717",
    "6336637947852365586", "6336876696494417749", "6334678278829252492",
    "6337087411884923105", "6336989731443711607", "6336882614959349480",
    "6336886055228153516", "6336797591786757523", "6336674519498890396",
    "6336856849450540332", "6337048379222138619", "6336816932024491505",
    "6336672814396874442", "6336835035311644293", "6336668004033504924",
    "6336682357814205676", "6336764563488252026", "6337100812182887680",
    "6336575056646249129"
]

# --- Premium Emoji Helper Functions ---

def get_emoji(key: str) -> str:
    """Get emoji character for a key."""
    char, _ = CUSTOM_EMOJIS.get(key, ("❓", None))
    return char

def get_emoji_entity(key: str, offset: int) -> Optional[MessageEntity]:
    """Get custom emoji entity for a key."""
    char, emoji_id = CUSTOM_EMOJIS.get(key, ("❓", None))
    if emoji_id:
        return MessageEntity(
            type="custom_emoji",
            offset=offset,
            length=len(char),
            custom_emoji_id=emoji_id
        )
    return None

def get_random_premium_emoji_id() -> str:
    """Get a random premium emoji ID from the list."""
    return random.choice(PREMIUM_EMOJIS)


def process_text_with_premium_emojis(text, entities=None):
    if entities is None:
        entities = []

    final_text = ""
    new_entities = []
    offset = 0

    for char in text:
        if emoji.is_emoji(char):
            emoji_id = get_random_premium_emoji_id()
            placeholder = "✨"

            new_entities.append(MessageEntity(
                type="custom_emoji",
                offset=offset,
                length=len(placeholder.encode("utf-16-le")) // 2,
                custom_emoji_id=emoji_id
            ))

            final_text += placeholder
            offset += len(placeholder.encode("utf-16-le")) // 2
        else:
            final_text += char
            offset += len(char.encode("utf-16-le")) // 2

    return final_text, new_entities


def create_premium_response(text: str, emoji_key: str = None, bold: bool = True, 
                           code_words: List[str] = None, italic: bool = False) -> tuple:
    """
    Create a complete response with premium emojis everywhere
    """
    final_text = text
    entities = []
    offset = 0
    
    # Add emoji at start
    if emoji_key:
        emoji_char, _ = CUSTOM_EMOJIS.get(emoji_key, ("❓", None))
        if emoji_char:
            final_text = f"{emoji_char} {text}"
            ent = get_emoji_entity(emoji_key, 0)
            if ent:
                entities.append(ent)
                offset = len(emoji_char) + 1
    
    # Add bold formatting
    if bold:
        entities.append(MessageEntity(
            type="bold",
            offset=0,
            length=len(final_text)
        ))
    
    # Add italic formatting
    if italic:
        entities.append(MessageEntity(
            type="italic",
            offset=0,
            length=len(final_text)
        ))
    
    # Add code formatting for specific words
    if code_words:
        for word in code_words:
            idx = final_text.find(str(word))
            if idx != -1:
                entities.append(MessageEntity(
                    type="code",
                    offset=idx,
                    length=len(str(word))
                ))
    
    # Process premium emojis in the text
    processed_text, new_entities = process_text_with_premium_emojis(final_text, entities)
    
    return processed_text, new_entities if new_entities else None

def add_premium_emojis_to_text(text: str) -> tuple:
    """
    Add premium emojis to any text
    """
    # Process all emojis in text
    return process_text_with_premium_emojis(text)

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables
application = None
scheduler = None

# --- Helper Functions for Data Storage ---

def is_owner(user_id):
    return user_id == OWNER_ID

def is_allowed_group(chat_id):
    data = load_data()
    allowed_groups = data.get("allowed_groups", [])
    if not allowed_groups:
        return False
    return chat_id in allowed_groups

def is_private_chat(update):
    return update.effective_chat.type == 'private'

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading data: {e}")
            return initialize_data()
    else:
        return initialize_data()

def initialize_data():
    return {
        "users": {}, 
        "total_likes": {}, 
        "custom_message": "",
        "allowed_groups": [],
        "auto_like_uids": {},
        "paused_uids": [],
        "settings": {"daily_like_time": DAILY_LIKE_TIME},
        "like_limits": {},
        "api_stats": {"total_calls": 0, "successful_calls": 0, "failed_calls": 0},
        "active_groups": []
    }

def save_data(data):
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
            json.dump(data, tmp, indent=4)
            tmp.flush()
        shutil.move(tmp.name, DATA_FILE)
    except IOError as e:
        logger.error(f"Error saving data: {e}")
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)

def format_uid_key(user_id, uid):
    return f"{user_id}_{uid}"

def parse_uid_key(key):
    parts = key.split('_', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, None

def update_user_info(data, user):
    user_id = str(user.id)
    telegram_name = user.first_name or ""
    if user.last_name:
        telegram_name += f" {user.last_name}"
    username = user.username or "N/A"
    
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "telegram_name": telegram_name,
            "username": username,
            "uid": None
        }
    else:
        data["users"][user_id]["telegram_name"] = telegram_name
        data["users"][user_id]["username"] = username
    
    return data

def update_group_info(data, chat):
    chat_id = str(chat.id)
    chat_title = chat.title or "Unknown Group"
    
    if "active_groups" not in data:
        data["active_groups"] = []
    
    group_exists = False
    for group in data["active_groups"]:
        if group["chat_id"] == chat_id:
            group["chat_title"] = chat_title
            group_exists = True
            break
    
    if not group_exists:
        data["active_groups"].append({
            "chat_id": chat_id,
            "chat_title": chat_title,
            "added_date": datetime.now(IST).isoformat()
        })
    
    return data

# --- Security Decorators ---

def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_owner(update.effective_user.id):
            text, entities = create_premium_response(
                "Access Denied! This command is only available to the bot owner.",
                emoji_key="error",
                bold=True
            )
            await update.message.reply_text(text, entities=entities)
            logger.warning(f"Unauthorized access attempt by user {update.effective_user.id}")
            return
        return await func(update, context)
    return wrapper

# --- API Helper Functions ---

async def call_like_api(uid, region="IND", retry_count=0):
    max_retries = 3
    api_url = "https://like-api-by-kamod.onrender.com/like"

    try:
        response = requests.get(
            api_url,
            params={
                "uid": str(uid),
                "server_name": str(region).upper()
            },
            timeout=45
        )
        response.raise_for_status()
        api_data = response.json()

        if not isinstance(api_data, dict):
            raise ValueError("API returned an unexpected response")

        data = load_data()
        data.setdefault("api_stats", {})
        data["api_stats"]["total_calls"] = (
            data["api_stats"].get("total_calls", 0) + 1
        )
        data["api_stats"]["successful_calls"] = (
            data["api_stats"].get("successful_calls", 0) + 1
        )
        save_data(data)

        return api_data

    except Exception as e:
        logger.error(f"API Error for UID {uid}: {e}")

        if retry_count < max_retries:
            await asyncio.sleep(5 * (2 ** retry_count))
            return await call_like_api(
                uid, region, retry_count + 1
            )

        data = load_data()
        data.setdefault("api_stats", {})
        data["api_stats"]["total_calls"] = (
            data["api_stats"].get("total_calls", 0) + 1
        )
        data["api_stats"]["failed_calls"] = (
            data["api_stats"].get("failed_calls", 0) + 1
        )
        save_data(data)

        raise Exception("API service temporarily unavailable")


async def send_like_response(update, context, api_data, uid, region, remaining_days, is_daily=False):
    try:
        # Build response with premium emojis
        prefix = "✨ Daily Auto-Like Results ✨" if is_daily else "✨ Like Results ✨"
        
        response_text = (
            f"{prefix}\n\n"
            f"{get_emoji('user')} Player Nickname: {api_data.get('PlayerNickname', 'N/A')}\n"
            f"{get_emoji('uid')} UID: {api_data.get('UID', 'N/A')}\n"
            f"{get_emoji('level')} Player Level: {api_data.get('PlayerLevel', 'N/A')}\n"
            f"{get_emoji('region')} Player Region: {api_data.get('PlayerRegion', 'N/A')}\n"
            f"{get_emoji('like')} Likes Before: {api_data.get('LikesbeforeCommand', 'N/A')}\n"
            f"{get_emoji('like')} Likes After: {api_data.get('LikesafterCommand', 'N/A')}\n"
            f"{get_emoji('like')} Likes Given by Bot: {api_data.get('LikesGivenByAPI', 'N/A')}\n"
            f"{get_emoji('days')} Days Remaining: {remaining_days}\n"
            f"{get_emoji('success')} Status: {api_data.get('status', 'N/A')}\n"
            f"{get_emoji('time')} Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )

        data = load_data()
        custom_message = data.get("custom_message", "")
        if custom_message:
            response_text += f"\n\n✨ {custom_message}"

        # Process premium emojis
        final_text, entities = process_text_with_premium_emojis(response_text)
        
        # Add bold formatting
        if entities is None:
            entities = []
        entities.append(MessageEntity(
            type="bold",
            offset=0,
            length=len(final_text)
        ))

        if is_daily:
            await application.bot.send_message(
                chat_id=update,
                text=final_text,
                entities=entities
            )
            await send_to_all_groups(final_text, entities)
        else:
            await update.message.reply_text(final_text, entities=entities)
            if not is_private_chat(update):
                await send_to_all_groups(final_text, entities)

        # Update user stats
        user_id = str(update.effective_user.id) if not is_daily else str(update)
        data = load_data()
        if user_id not in data["users"]:
            if not is_daily:
                user = update.effective_user
                telegram_name = user.first_name or ""
                if user.last_name:
                    telegram_name += f" {user.last_name}"
                username = user.username or "N/A"
            else:
                telegram_name = f"User {user_id}"
                username = "N/A"
            
            data["users"][user_id] = {
                "telegram_name": telegram_name,
                "username": username,
                "uid": uid
            }
        else:
            if not is_daily:
                user = update.effective_user
                telegram_name = user.first_name or ""
                if user.last_name:
                    telegram_name += f" {user.last_name}"
                username = user.username or "N/A"
                
                data["users"][user_id]["telegram_name"] = telegram_name
                data["users"][user_id]["username"] = username

        if "LikesGivenByAPI" in api_data:
            if user_id not in data["total_likes"]:
                data["total_likes"][user_id] = {"count": 0, "days": 0}
            data["total_likes"][user_id]["count"] += api_data["LikesGivenByAPI"]
            data["total_likes"][user_id]["days"] += 1
            save_data(data)

        return True
    except Exception as e:
        logger.error(f"Error sending like response: {e}")
        return False

async def send_to_all_groups(message, entities=None):
    try:
        data = load_data()
        active_groups = data.get("active_groups", [])
        
        for group in active_groups:
            try:
                await application.bot.send_message(
                    chat_id=group["chat_id"],
                    text=message,
                    entities=entities
                )
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to send message to group {group['chat_id']}: {e}")
                data["active_groups"] = [g for g in data["active_groups"] if g["chat_id"] != group["chat_id"]]
                save_data(data)
    except Exception as e:
        logger.error(f"Error in send_to_all_groups: {e}")

# --- Scheduler Management ---

async def reschedule_daily_job():
    global scheduler
    if not scheduler:
        return

    data = load_data()
    daily_time = data.get("settings", {}).get("daily_like_time", DAILY_LIKE_TIME)
    hour, minute = map(int, daily_time.split(':'))

    try:
        scheduler.remove_job("daily_like_job")
    except JobLookupError:
        pass
    except Exception as e:
        logger.error(f"Error removing daily job: {e}")

    scheduler.add_job(
        daily_like_job,
        trigger=CronTrigger(hour=hour, minute=minute),
        id='daily_like_job',
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=600
    )
    logger.info(f"Daily like job scheduled for {hour:02d}:{minute:02d} IST")

# --- Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    
    if not is_private_chat(update):
        data = update_group_info(data, update.effective_chat)
    
    save_data(data)
    
    text, entities = create_premium_response(
        "✨ Welcome to the Auto-Like Bot ✨\n\n"
        "🤖 This bot helps you automatically send likes to your game UID daily.\n\n"
        "📋 Use /help to see all available commands.",
        emoji_key="welcome",
        bold=True
    )
    
    await update.message.reply_text(text, entities=entities)
    logger.info(f"User {update.effective_user.id} started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command with premium emojis on every command"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    
    if not is_private_chat(update):
        data = update_group_info(data, update.effective_chat)
    
    save_data(data)
    
    help_text = (
        "✨ Auto-Like Bot Commands ✨\n\n"
        "📋 User Commands:\n"
        "⭐ /help - Show this help message\n"
        "⭐ /start - Welcome message\n"
        "⭐ /mylike - Check your total likes\n"
        "⭐ /myuids - Show all your registered UIDs\n\n"
        "👑 Owner Commands:\n"
        "⭐ /autolike {uid} {region} {days} - Set automatic daily likes\n"
        "⭐ /like {uid} {region} - Send single like request\n"
        "⭐ /status - See who is using the bot\n"
        "⭐ /setmessage <text> - Set custom autolike response message\n"
        "⭐ /setgroup {group_id} - Add group to allowed groups\n"
        "⭐ /removeuid {uid} - Remove a UID from auto-likes\n"
        "⭐ /pauseuid {uid} - Pause auto-likes for a UID\n"
        "⭐ /resumeuid {uid} - Resume auto-likes for a UID\n"
        "⭐ /extend {uid} {days} - Extend auto-like days for a UID\n"
        "⭐ /resetlikes {uid} - Reset likes count of a UID\n"
        "⭐ /ownerbroadcast <message> - Broadcast a message to all users\n"
        "⭐ /allstats - Show total stats\n"
        "⭐ /backup - Export bot data backup\n"
        "⭐ /restore - Restore from backup\n"
        "⭐ /settime {hour}:{minute} - Change daily auto-like time\n"
        "⭐ /setlimit {uid} {limit} - Set daily like limit for a UID\n"
        "⭐ /checkapi {uid} {region} - Test API call for a UID\n"
        "⭐ /runnow - Run daily auto-like job immediately\n"
        "⭐ /groups - Show all active groups\n\n"
        "📝 Usage Examples:\n"
        "🔥 /autolike 1234567890 US 30\n"
        "🔥 /like 1234567890 US\n"
        "🔥 /extend 1234567890 7\n"
        "🔥 /settime 04:30\n"
        "🔥 /setlimit 1234567890 50"
    )
    
    text, entities = create_premium_response(
        help_text,
        emoji_key="help",
        bold=True
    )
    
    await update.message.reply_text(text, entities=entities)
    logger.info(f"User {update.effective_user.id} requested help")

@owner_only
async def autolike(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Setup auto-like with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if len(context.args) not in [3, 4]:
        text, entities = create_premium_response(
            "Usage:\n"
            "⭐ /autolike {uid} {region} {days}\n"
            "⭐ /autolike {uid} {region} {days} {user_id}",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return

    uid = context.args[0]
    region = context.args[1].upper()
    try:
        days = int(context.args[2])
        if days <= 0:
            text, entities = create_premium_response(
                "Days must be a positive number.",
                emoji_key="error",
                bold=True
            )
            await update.message.reply_text(text, entities=entities)
            return
    except ValueError:
        text, entities = create_premium_response(
            "Days must be a valid number.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return

    if len(context.args) == 4:
        target_user_id = str(context.args[3])
        try:
            user_obj = await context.bot.get_chat(target_user_id)
            telegram_name = user_obj.first_name or ""
            if user_obj.last_name:
                telegram_name += f" {user_obj.last_name}"
            username = user_obj.username or "N/A"
            data["users"][target_user_id] = {
                "telegram_name": telegram_name,
                "username": username,
                "uid": uid
            }
            save_data(data)
        except Exception as e:
            logger.warning(f"Could not fetch target user info: {e}")
    else:
        target_user_id = str(update.effective_user.id)

    data = load_data()
    uid_key = format_uid_key(target_user_id, uid)
    expiry_date = (datetime.now(IST) + timedelta(days=days)).isoformat()

    if "auto_like_uids" not in data:
        data["auto_like_uids"] = {}

    if uid_key in data["auto_like_uids"]:
        existing_expiry = datetime.fromisoformat(data["auto_like_uids"][uid_key]["expiry_date"]).astimezone(IST)
        new_expiry = existing_expiry + timedelta(days=days)
        data["auto_like_uids"][uid_key]["expiry_date"] = new_expiry.isoformat()
        data["auto_like_uids"][uid_key]["region"] = region
        action = "updated"
    else:
        data["auto_like_uids"][uid_key] = {
            "uid": uid,
            "region": region,
            "expiry_date": expiry_date,
            "chat_id": target_user_id,
            "paused": False,
            "last_run": None,
            "total_likes": 0
        }
        action = "activated"

    if uid_key in data.get("paused_uids", []):
        data["paused_uids"].remove(uid_key)

    save_data(data)

    try:
        api_data = await call_like_api(uid, region)
        remaining_days = max(0, (datetime.fromisoformat(expiry_date).astimezone(IST) - datetime.now(IST)).days)
        await send_like_response(update, context, api_data, uid, region, remaining_days, is_daily=False)

        data = load_data()
        if uid_key in data["auto_like_uids"]:
            data["auto_like_uids"][uid_key]["total_likes"] += api_data.get("LikesGivenByAPI", 0)
            data["auto_like_uids"][uid_key]["last_run"] = datetime.now(IST).isoformat()
            save_data(data)
    except Exception as e:
        logger.error(f"Error in autolike command: {e}")
        text, entities = create_premium_response(
            "Error calling the API. Please try again later.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return

    daily_time = data.get("settings", {}).get("daily_like_time", DAILY_LIKE_TIME)

    if len(context.args) == 4:
        text, entities = create_premium_response(
            f"✅ Auto-like {action} for user {target_user_id}!\n"
            f"🔢 UID: {uid}\n"
            f"🌍 Region: {region}\n"
            f"📅 Days: {days}\n\n"
            f"🔄 Automatic likes will be sent daily at {daily_time} IST.",
            emoji_key="success",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"✨ Auto-like has been {action} for your UID! ✨\n\n"
                     f"🔢 UID: {uid}\n"
                     f"🌍 Region: {region}\n"
                     f"📅 Days: {days}\n"
                     f"⏰ Daily Time: {daily_time} IST"
            )
        except Exception as e:
            logger.error(f"Failed to send message to user {target_user_id}: {e}")
    else:
        text, entities = create_premium_response(
            f"✅ Auto-like {action}!\n"
            f"🔢 UID: {uid}\n"
            f"🌍 Region: {region}\n"
            f"📅 Days: {days}\n\n"
            f"🔄 Automatic likes will be sent daily at {daily_time} IST.",
            emoji_key="success",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

    logger.info(f"Owner set autolike for UID {uid} -> target user {target_user_id}")

@owner_only
async def like(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a single like request with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if len(context.args) != 2:
        text, entities = create_premium_response(
            "Usage: /like {uid} {region}",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return

    uid = context.args[0]
    region = context.args[1].upper()
    
    try:
        api_data = await call_like_api(uid, region)
        await send_like_response(update, context, api_data, uid, region, "1", is_daily=False)
        logger.info(f"Owner {update.effective_user.id} sent like to UID {uid}")
    except Exception as e:
        logger.error(f"Error in like command: {e}")
        text, entities = create_premium_response(
            "Error calling the API. Please try again later.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

@owner_only
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Status command with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    data = load_data()
    users = data.get("users", {})
    auto_like_uids = data.get("auto_like_uids", {})
    allowed_groups = data.get("allowed_groups", [])
    paused_uids = data.get("paused_uids", [])
    api_stats = data.get("api_stats", {})
    active_groups = data.get("active_groups", [])

    response_text = "✨ Bot Status ✨\n\n"
    
    response_text += f"📈 API Statistics:\n"
    response_text += f"⭐ Total Calls: {api_stats.get('total_calls', 0)}\n"
    response_text += f"⭐ Successful: {api_stats.get('successful_calls', 0)}\n"
    response_text += f"⭐ Failed: {api_stats.get('failed_calls', 0)}\n\n"
    
    if active_groups:
        response_text += f"🏢 Active Groups: {len(active_groups)}\n"
        for group in active_groups:
            response_text += f"⭐ {group['chat_title']} (ID: {group['chat_id']})\n"
        response_text += "\n"
    
    if users:
        response_text += f"👥 Users: {len(users)}\n"
        for user_id, user_info in users.items():
            response_text += (
                f"⭐ {user_info.get('telegram_name', 'Unknown')}\n"
                f"  ID: {user_id}\n"
                f"  Username: @{user_info.get('username', 'N/A')}\n"
                f"  UID: {user_info.get('uid', 'N/A')}\n\n"
            )
    
    if auto_like_uids:
        response_text += f"🔄 Auto-Like UIDs: {len(auto_like_uids)}\n"
        for uid_key, uid_info in auto_like_uids.items():
            user_id, uid = parse_uid_key(uid_key)
            user_info = users.get(user_id, {})
            user_name = user_info.get('telegram_name', 'Unknown')
            username = user_info.get('username', 'N/A')
            last_run = datetime.fromisoformat(uid_info['last_run']).astimezone(IST).strftime('%Y-%m-%d %H:%M') if uid_info.get('last_run') else 'Never'
            is_paused = uid_key in paused_uids
            status = "⏸️ Paused" if is_paused else "✅ Active"
            
            expiry_date = datetime.fromisoformat(uid_info['expiry_date']).astimezone(IST)
            remaining_days = max(0, (expiry_date - datetime.now(IST)).days)
            
            response_text += (
                f"⭐ {user_name} (@{username}) ({status})\n"
                f"  UID: {uid_info['uid']}\n"
                f"  Region: {uid_info['region']}\n"
                f"  Days Left: {remaining_days}\n"
                f"  Total Likes: {uid_info.get('total_likes', 0)}\n"
                f"  Last Run: {last_run}\n\n"
            )
    
    if allowed_groups:
        response_text += f"🏢 Allowed Groups: {len(allowed_groups)}\n"
        for group_id in allowed_groups:
            response_text += f"⭐ {group_id}\n"
    
    text, entities = create_premium_response(
        response_text,
        emoji_key="status",
        bold=True
    )
    
    await update.message.reply_text(text, entities=entities)
    logger.info(f"Owner {update.effective_user.id} checked status")

async def mylike(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check personal likes with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    
    if not is_private_chat(update):
        data = update_group_info(data, update.effective_chat)
    
    save_data(data)
    
    data = load_data()
    user_id = str(update.effective_user.id)
    user_likes = data.get("total_likes", {}).get(user_id)

    if user_likes:
        response_text = (
            f"📊 Your Like Stats:\n\n"
            f"❤️ Total Likes Received: {user_likes['count']}\n"
            f"📅 Total Days Used: {user_likes['days']}"
        )
        text, entities = create_premium_response(
            response_text,
            emoji_key="stats",
            bold=True
        )
    else:
        text, entities = create_premium_response(
            "You have not received any likes yet.",
            emoji_key="info",
            bold=True
        )

    await update.message.reply_text(text, entities=entities)
    logger.info(f"User {user_id} checked their likes")

@owner_only
async def setmessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set custom message with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if not context.args:
        text, entities = create_premium_response(
            "Usage: /setmessage <your_message_here>",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return

    custom_message = ' '.join(context.args)
    data = load_data()
    data["custom_message"] = custom_message
    save_data(data)
    
    text, entities = create_premium_response(
        f"✅ The autolike response message has been set to:\n\n✨ {custom_message}",
        emoji_key="success",
        bold=True
    )
    await update.message.reply_text(text, entities=entities)
    logger.info(f"Owner {update.effective_user.id} set custom message")

@owner_only
async def setgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add group with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if not context.args:
        text, entities = create_premium_response(
            "Usage: /setgroup {group_id}\n\nExample: /setgroup -1001234567890",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return

    try:
        group_id = int(context.args[0])
        data = load_data()
        
        if "allowed_groups" not in data:
            data["allowed_groups"] = []
        
        if group_id not in data["allowed_groups"]:
            data["allowed_groups"].append(group_id)
            save_data(data)
            
            text, entities = create_premium_response(
                f"✅ Group {group_id} has been added to allowed groups.",
                emoji_key="success",
                bold=True
            )
            await update.message.reply_text(text, entities=entities)
            logger.info(f"Owner {update.effective_user.id} added group {group_id}")
        else:
            text, entities = create_premium_response(
                f"ℹ️ Group {group_id} is already in the allowed groups list.",
                emoji_key="info",
                bold=True
            )
            await update.message.reply_text(text, entities=entities)
            
    except ValueError:
        text, entities = create_premium_response(
            "Invalid group ID. Please provide a valid numeric group ID.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

async def myuids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all registered UIDs with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    
    if not is_private_chat(update):
        data = update_group_info(data, update.effective_chat)
    
    save_data(data)
    
    data = load_data()
    user_id = str(update.effective_user.id)
    auto_like_uids = data.get("auto_like_uids", {})
    paused_uids = data.get("paused_uids", [])
    
    user_uids = {}
    for uid_key, uid_info in auto_like_uids.items():
        key_user_id, uid = parse_uid_key(uid_key)
        if key_user_id == user_id:
            user_uids[uid] = {
                **uid_info,
                "paused": uid_key in paused_uids
            }
    
    if not user_uids:
        text, entities = create_premium_response(
            "You don't have any UIDs registered for auto-likes.",
            emoji_key="info",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    response_text = "📋 Your Registered UIDs:\n\n"
    for uid, info in user_uids.items():
        status = "⏸️ Paused" if info["paused"] else "✅ Active"
        last_run = datetime.fromisoformat(info['last_run']).astimezone(IST).strftime('%Y-%m-%d %H:%M') if info.get('last_run') else 'Never'
        
        expiry_date = datetime.fromisoformat(info['expiry_date']).astimezone(IST)
        remaining_days = max(0, (expiry_date - datetime.now(IST)).days)
        
        response_text += (
            f"🔢 UID: {uid}\n"
            f"🌍 Region: {info['region']}\n"
            f"📅 Days Remaining: {remaining_days}\n"
            f"❤️ Total Likes: {info.get('total_likes', 0)}\n"
            f"🔄 Status: {status}\n"
            f"⏰ Last Run: {last_run}\n\n"
        )
    
    text, entities = create_premium_response(
        response_text,
        emoji_key="uid",
        bold=True
    )
    await update.message.reply_text(text, entities=entities)
    logger.info(f"User {user_id} checked their UIDs")

@owner_only
async def remove_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove UID with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if not context.args:
        text, entities = create_premium_response(
            "Usage: /removeuid {uid}",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    uid_to_remove = context.args[0]
    data = load_data()
    user_id = str(update.effective_user.id)
    uid_key = format_uid_key(user_id, uid_to_remove)
    
    if uid_key in data.get("auto_like_uids", {}):
        del data["auto_like_uids"][uid_key]
        
        if uid_key in data.get("paused_uids", []):
            data["paused_uids"].remove(uid_key)
            
        save_data(data)
        
        text, entities = create_premium_response(
            f"✅ UID {uid_to_remove} has been removed from auto-likes.",
            emoji_key="success",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        logger.info(f"Owner {user_id} removed UID {uid_to_remove}")
    else:
        text, entities = create_premium_response(
            f"❌ You don't have auto-likes set up for UID {uid_to_remove}.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

@owner_only
async def pause_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pause UID with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if not context.args:
        text, entities = create_premium_response(
            "Usage: /pauseuid {uid}",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    uid_to_pause = context.args[0]
    data = load_data()
    user_id = str(update.effective_user.id)
    uid_key = format_uid_key(user_id, uid_to_pause)
    
    if uid_key in data.get("auto_like_uids", {}):
        if "paused_uids" not in data:
            data["paused_uids"] = []
        
        if uid_key not in data["paused_uids"]:
            data["paused_uids"].append(uid_key)
            save_data(data)
            
            text, entities = create_premium_response(
                f"✅ Auto-likes for UID {uid_to_pause} have been paused.",
                emoji_key="success",
                bold=True
            )
            await update.message.reply_text(text, entities=entities)
            logger.info(f"Owner {user_id} paused UID {uid_to_pause}")
        else:
            text, entities = create_premium_response(
                f"ℹ️ Auto-likes for UID {uid_to_pause} are already paused.",
                emoji_key="info",
                bold=True
            )
            await update.message.reply_text(text, entities=entities)
    else:
        text, entities = create_premium_response(
            f"❌ You don't have auto-likes set up for UID {uid_to_pause}.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

@owner_only
async def resume_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resume UID with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if not context.args:
        text, entities = create_premium_response(
            "Usage: /resumeuid {uid}",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    uid_to_resume = context.args[0]
    data = load_data()
    user_id = str(update.effective_user.id)
    uid_key = format_uid_key(user_id, uid_to_resume)
    
    if uid_key in data.get("auto_like_uids", {}):
        if uid_key in data.get("paused_uids", []):
            data["paused_uids"].remove(uid_key)
            save_data(data)
            
            text, entities = create_premium_response(
                f"✅ Auto-likes for UID {uid_to_resume} have been resumed.",
                emoji_key="success",
                bold=True
            )
            await update.message.reply_text(text, entities=entities)
            logger.info(f"Owner {user_id} resumed UID {uid_to_resume}")
        else:
            text, entities = create_premium_response(
                f"ℹ️ Auto-likes for UID {uid_to_resume} are not paused.",
                emoji_key="info",
                bold=True
            )
            await update.message.reply_text(text, entities=entities)
    else:
        text, entities = create_premium_response(
            f"❌ You don't have auto-likes set up for UID {uid_to_resume}.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

@owner_only
async def extend_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extend UID with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if len(context.args) != 2:
        text, entities = create_premium_response(
            "Usage: /extend {uid} {days}",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    uid_to_extend = context.args[0]
    try:
        days = int(context.args[1])
        if days <= 0:
            text, entities = create_premium_response(
                "Days must be a positive number.",
                emoji_key="error",
                bold=True
            )
            await update.message.reply_text(text, entities=entities)
            return
    except ValueError:
        text, entities = create_premium_response(
            "Days must be a valid number.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    data = load_data()
    user_id = str(update.effective_user.id)
    uid_key = format_uid_key(user_id, uid_to_extend)
    
    if uid_key in data.get("auto_like_uids", {}):
        current_expiry = datetime.fromisoformat(data["auto_like_uids"][uid_key]["expiry_date"]).astimezone(IST)
        new_expiry = current_expiry + timedelta(days=days)
        data["auto_like_uids"][uid_key]["expiry_date"] = new_expiry.isoformat()
        save_data(data)
        
        remaining_days = max(0, (new_expiry - datetime.now(IST)).days)
        
        text, entities = create_premium_response(
            f"✅ Auto-likes for UID {uid_to_extend} extended by {days} days.\n"
            f"📅 New expiry: {new_expiry.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"⏰ Days remaining: {remaining_days}",
            emoji_key="success",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        logger.info(f"Owner {user_id} extended UID {uid_to_extend} by {days} days")
    else:
        text, entities = create_premium_response(
            f"❌ You don't have auto-likes set up for UID {uid_to_extend}.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

@owner_only
async def reset_likes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset likes with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if not context.args:
        text, entities = create_premium_response(
            "Usage: /resetlikes {uid}",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    uid_to_reset = context.args[0]
    data = load_data()
    user_id = str(update.effective_user.id)
    uid_key = format_uid_key(user_id, uid_to_reset)
    
    if uid_key in data.get("auto_like_uids", {}):
        data["auto_like_uids"][uid_key]["total_likes"] = 0
        save_data(data)
        
        text, entities = create_premium_response(
            f"✅ Like count for UID {uid_to_reset} has been reset to 0.",
            emoji_key="success",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        logger.info(f"Owner {user_id} reset likes for UID {uid_to_reset}")
    else:
        text, entities = create_premium_response(
            f"❌ You don't have auto-likes set up for UID {uid_to_reset}.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

@owner_only
async def owner_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if not context.args:
        text, entities = create_premium_response(
            "Usage: /ownerbroadcast <message>",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    message = ' '.join(context.args)
    data = load_data()
    users = data.get("users", {})
    
    sent_count = 0
    failed_count = 0
    
    for user_id in users.keys():
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 Broadcast from Owner:\n\n✨ {message}"
            )
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send broadcast to user {user_id}: {e}")
            failed_count += 1
    
    text, entities = create_premium_response(
        f"📢 Broadcast completed!\n"
        f"✅ Sent: {sent_count}\n"
        f"❌ Failed: {failed_count}",
        emoji_key="broadcast",
        bold=True,
        code_words=[str(sent_count), str(failed_count)]
    )
    await update.message.reply_text(text, entities=entities)
    logger.info(f"Owner {update.effective_user.id} sent broadcast to {sent_count} users")

@owner_only
async def allstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """All statistics with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    data = load_data()
    users = data.get("users", {})
    auto_like_uids = data.get("auto_like_uids", {})
    total_likes = data.get("total_likes", {})
    api_stats = data.get("api_stats", {})
    active_groups = data.get("active_groups", [])
    
    total_users = len(users)
    total_auto_likes = len(auto_like_uids)
    total_likes_sent = sum(info.get("total_likes", 0) for info in auto_like_uids.values())
    
    active_uids = 0
    paused_uids = 0
    expired_uids = 0
    
    for uid_key, uid_info in auto_like_uids.items():
        expiry_date = datetime.fromisoformat(uid_info["expiry_date"]).astimezone(IST)
        if expiry_date < datetime.now(IST):
            expired_uids += 1
        elif uid_key in data.get("paused_uids", []):
            paused_uids += 1
        else:
            active_uids += 1
    
    response_text = (
        f"📊 Comprehensive Statistics:\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🏢 Active Groups: {len(active_groups)}\n"
        f"🔄 Total Auto-Like UIDs: {total_auto_likes}\n"
        f"✅ Active UIDs: {active_uids}\n"
        f"⏸️ Paused UIDs: {paused_uids}\n"
        f"❌ Expired UIDs: {expired_uids}\n"
        f"❤️ Total Likes Sent: {total_likes_sent}\n\n"
        f"📈 API Statistics:\n"
        f"⭐ Total Calls: {api_stats.get('total_calls', 0)}\n"
        f"⭐ Successful: {api_stats.get('successful_calls', 0)}\n"
        f"⭐ Failed: {api_stats.get('failed_calls', 0)}\n"
        f"⭐ Success Rate: {api_stats.get('successful_calls', 0) / max(api_stats.get('total_calls', 1), 1) * 100:.1f}%"
    )
    
    text, entities = create_premium_response(
        response_text,
        emoji_key="stats",
        bold=True
    )
    await update.message.reply_text(text, entities=entities)
    logger.info(f"Owner {update.effective_user.id} checked all stats")

@owner_only
async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Backup with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    try:
        with open(DATA_FILE, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename="bot_data_backup.json",
                caption="📦 Bot Data Backup"
            )
        logger.info(f"Owner {update.effective_user.id} exported backup")
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        text, entities = create_premium_response(
            "Backup failed. Check logs for details.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

@owner_only
async def restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restore with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if not update.message.document:
        text, entities = create_premium_response(
            "Please send a backup file to restore.",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    try:
        file = await context.bot.get_file(update.message.document.file_id)
        await file.download_to_drive("restore_backup.json")
        
        with open("restore_backup.json", 'r') as f:
            backup_data = json.load(f)
        
        if not isinstance(backup_data, dict):
            raise ValueError("Invalid backup format")
        
        with open(DATA_FILE, 'w') as f:
            json.dump(backup_data, f, indent=4)
        
        text, entities = create_premium_response(
            "Backup restored successfully!",
            emoji_key="success",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        logger.info(f"Owner {update.effective_user.id} restored backup")
        
        if os.path.exists("restore_backup.json"):
            os.remove("restore_backup.json")
            
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        text, entities = create_premium_response(
            "Restore failed. Invalid backup file or format.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

@owner_only
async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set time with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if not context.args:
        text, entities = create_premium_response(
            "Usage: /settime {hour}:{minute}\n\nExample: /settime 04:30",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    time_str = context.args[0]
    if not re.match(r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$', time_str):
        text, entities = create_premium_response(
            "Invalid time format. Please use HH:MM (24-hour format).",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    data = load_data()
    if "settings" not in data:
        data["settings"] = {}
    
    data["settings"]["daily_like_time"] = time_str
    save_data(data)
    
    await reschedule_daily_job()
    
    text, entities = create_premium_response(
        f"✅ Daily auto-like time set to {time_str} IST.",
        emoji_key="success",
        bold=True
    )
    await update.message.reply_text(text, entities=entities)
    logger.info(f"Owner {update.effective_user.id} set daily time to {time_str}")

@owner_only
async def set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set limit with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if len(context.args) != 2:
        text, entities = create_premium_response(
            "Usage: /setlimit {uid} {limit}",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    uid = context.args[0]
    try:
        limit = int(context.args[1])
        if limit <= 0:
            text, entities = create_premium_response(
                "Limit must be a positive number.",
                emoji_key="error",
                bold=True
            )
            await update.message.reply_text(text, entities=entities)
            return
    except ValueError:
        text, entities = create_premium_response(
            "Limit must be a valid number.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    data = load_data()
    user_id = str(update.effective_user.id)
    uid_key = format_uid_key(user_id, uid)
    
    if uid_key in data.get("auto_like_uids", {}):
        if "like_limits" not in data:
            data["like_limits"] = {}
        
        data["like_limits"][uid_key] = limit
        save_data(data)
        
        text, entities = create_premium_response(
            f"✅ Daily like limit for UID {uid} set to {limit}.",
            emoji_key="success",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        logger.info(f"Owner {user_id} set limit {limit} for UID {uid}")
    else:
        text, entities = create_premium_response(
            f"❌ You don't have auto-likes set up for UID {uid}.",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

@owner_only
async def check_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check API with premium emojis"""
    data = load_data()
    data = update_user_info(data, update.effective_user)
    save_data(data)
    
    if len(context.args) != 2:
        text, entities = create_premium_response(
            "Usage: /checkapi {uid} {region}",
            emoji_key="warning",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    uid = context.args[0]
    region = context.args[1].upper()
    
    try:
        text, entities = create_premium_response(
            f"🔍 Testing API for UID {uid}, region {region}...",
            emoji_key="test",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        
        api_data = await call_like_api(uid, region)
        
        response_text = (
            f"✅ API Test Successful!\n\n"
            f"🔢 UID: {api_data.get('UID', 'N/A')}\n"
            f"👤 Player: {api_data.get('PlayerNickname', 'N/A')}\n"
            f"📊 Level: {api_data.get('PlayerLevel', 'N/A')}\n"
            f"🌍 Region: {api_data.get('PlayerRegion', 'N/A')}\n"
            f"❤️ Likes Before: {api_data.get('LikesbeforeCommand', 'N/A')}\n"
            f"❤️ Likes After: {api_data.get('LikesafterCommand', 'N/A')}\n"
            f"🤖 Likes Given: {api_data.get('LikesGivenByAPI', 'N/A')}\n"
            f"✅ Status: {api_data.get('status', 'N/A')}"
        )
        
        text, entities = create_premium_response(
            response_text,
            emoji_key="success",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        logger.info(f"Owner {update.effective_user.id} tested API for UID {uid}")
        
    except Exception as e:
        logger.error(f"API test failed for UID {uid}: {e}")
        text, entities = create_premium_response(
            f"API test failed: {str(e)}",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

@owner_only
async def runnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run job immediately with premium emojis"""
    text, entities = create_premium_response(
        "⏳ Running daily auto-like job now...",
        emoji_key="processing",
        bold=True
    )
    await update.message.reply_text(text, entities=entities)
    
    try:
        await daily_like_job()
        
        text, entities = create_premium_response(
            "✅ Daily auto-like job completed!",
            emoji_key="completed",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        logger.info(f"Owner {update.effective_user.id} triggered runnow successfully")
    except Exception as e:
        logger.error(f"Error in runnow command: {e}")
        text, entities = create_premium_response(
            f"Error running daily job: {e}",
            emoji_key="error",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)

@owner_only
async def groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active groups with premium emojis"""
    data = load_data()
    active_groups = data.get("active_groups", [])
    
    if not active_groups:
        text, entities = create_premium_response(
            "ℹ️ No active groups found.",
            emoji_key="info",
            bold=True
        )
        await update.message.reply_text(text, entities=entities)
        return
    
    response_text = "🏢 Active Groups:\n\n"
    for group in active_groups:
        added_date = datetime.fromisoformat(group['added_date']).astimezone(IST).strftime('%Y-%m-%d %H:%M:%S')
        response_text += (
            f"📋 {group['chat_title']}\n"
            f"🆔 ID: {group['chat_id']}\n"
            f"📅 Added: {added_date}\n\n"
        )
    
    text, entities = create_premium_response(
        response_text,
        emoji_key="group",
        bold=True
    )
    await update.message.reply_text(text, entities=entities)
    logger.info(f"Owner {update.effective_user.id} checked active groups")

# --- Daily Job Function ---

async def daily_like_job():
    """Scheduled job to send daily auto-likes with premium emojis"""
    logger.info("🔄 Starting daily auto-like job...")
    
    data = load_data()
    auto_like_uids = data.get("auto_like_uids", {})
    paused_uids = data.get("paused_uids", [])
    
    if not auto_like_uids:
        logger.info("No auto-like UIDs found. Skipping daily job.")
        return
    
    expired_keys = []
    processed_count = 0
    success_count = 0
    failed_count = 0
    
    for uid_key, uid_info in auto_like_uids.items():
        if uid_key in paused_uids:
            continue
            
        expiry_date = datetime.fromisoformat(uid_info["expiry_date"]).astimezone(IST)
        if expiry_date <= datetime.now(IST):
            expired_keys.append(uid_key)
            continue
            
        processed_count += 1
        try:
            api_data = await call_like_api(uid_info["uid"], uid_info["region"])
            remaining_days = max(0, (expiry_date - datetime.now(IST)).days)
            
            await send_like_response(
                uid_info["chat_id"],
                None,
                api_data,
                uid_info["uid"],
                uid_info["region"],
                remaining_days,
                is_daily=True
            )
            
            data = load_data()
            if uid_key in data.get("auto_like_uids", {}):
                data["auto_like_uids"][uid_key]["total_likes"] += api_data.get("LikesGivenByAPI", 0)
                data["auto_like_uids"][uid_key]["last_run"] = datetime.now(IST).isoformat()
                save_data(data)
            
            success_count += 1
            logger.info(f"✅ Daily like sent for UID {uid_info['uid']}")
            
        except Exception as e:
            failed_count += 1
            logger.error(f"❌ Failed to send daily like for UID {uid_info['uid']}: {e}")
            
        await asyncio.sleep(1)
    
    if expired_keys:
        data = load_data()
        for key in expired_keys:
            if key in data.get("auto_like_uids", {}):
                del data["auto_like_uids"][key]
            if key in data.get("paused_uids", []):
                data["paused_uids"].remove(key)
        save_data(data)
        logger.info(f"🗑️ Removed {len(expired_keys)} expired UIDs")
    
    logger.info(
        f"✅ Daily job completed: "
        f"Processed: {processed_count}, "
        f"Success: {success_count}, "
        f"Failed: {failed_count}, "
        f"Expired: {len(expired_keys)}"
    )

# --- Main Function ---

async def on_startup(app: Application):
    """Startup hook to initialize scheduler"""
    global scheduler
    logger.info("🚀 Starting scheduler...")
    await reschedule_daily_job()
    asyncio.get_running_loop().call_soon(scheduler.start)
    logger.info("✅ Scheduler started successfully")

def main():
    """Main function to start the bot"""
    global application, scheduler
    
    scheduler = AsyncIOScheduler(timezone=IST)
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("autolike", autolike))
    application.add_handler(CommandHandler("like", like))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("mylike", mylike))
    application.add_handler(CommandHandler("myuids", myuids))
    application.add_handler(CommandHandler("setmessage", setmessage))
    application.add_handler(CommandHandler("setgroup", setgroup))
    application.add_handler(CommandHandler("removeuid", remove_uid))
    application.add_handler(CommandHandler("pauseuid", pause_uid))
    application.add_handler(CommandHandler("resumeuid", resume_uid))
    application.add_handler(CommandHandler("extend", extend_uid))
    application.add_handler(CommandHandler("resetlikes", reset_likes))
    application.add_handler(CommandHandler("ownerbroadcast", owner_broadcast))
    application.add_handler(CommandHandler("allstats", allstats))
    application.add_handler(CommandHandler("backup", backup))
    application.add_handler(CommandHandler("restore", restore))
    application.add_handler(CommandHandler("settime", set_time))
    application.add_handler(CommandHandler("setlimit", set_limit))
    application.add_handler(CommandHandler("checkapi", check_api))
    application.add_handler(CommandHandler("runnow", runnow))
    application.add_handler(CommandHandler("groups", groups))

    application.post_init = on_startup

    logger.info("🤖 Bot is starting with Premium Emojis...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    import asyncio

    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    main()