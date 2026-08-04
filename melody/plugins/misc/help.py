"""
📋 /help — Premium categorized help menu with attractive UI
"""
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from melody import bot
from melody.config import Config
from utils.decorators import error_handler

# ─── Help content ─────────────────────────────────────────────────────────────

HELP_TEXT = {
    "music": (
        "🎵 **Music Commands**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "`/play [song/url]` — ▶️ Play from YouTube\n"
        "`/vplay [song/url]` — 🎬 Video stream\n"
        "`/queue` `/q` — 📋 View the queue\n"
        "`/skip` `/s` — ⏭ Skip current song\n"
        "`/pause` — ⏸ Pause playback\n"
        "`/resume` — ▶️ Resume playback\n"
        "`/stop` — ⏹ Stop & clear queue\n"
        "`/seek [sec]` — ⏩ Seek forward\n"
        "`/rewind [sec]` — ⏪ Seek backward\n"
        "`/np` — 🎶 Now playing info\n"
        "`/shuffle` — 🔀 Shuffle the queue\n"
        "`/clearqueue` — 🗑 Clear entire queue\n"
        "`/remove [pos]` — ❌ Remove from queue\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ),
    "settings": (
        "⚙️ **Settings Commands**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "`/volume [1-200]` — 🔊 Set volume level\n"
        "`/mute` — 🔇 Mute audio\n"
        "`/unmute` — 🔈 Unmute audio\n"
        "`/loop` — 🔂 Loop current song\n"
        "`/loopall` — 🔁 Loop the entire queue\n"
        "`/noloop` — ➡️ Disable looping\n"
        "`/speed [0.5-2.0]` — ⏱ Playback speed\n"
        "`/autoplay on/off` — 🤖 Toggle autoplay\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ),
    "info": (
        "ℹ️ **Info & Utility**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "`/search [query]` — 🔍 Search YouTube\n"
        "`/lyrics [song]` — 🎤 Genius lyrics\n"
        "`/np` — 🎵 Now playing details\n"
        "`/ping` — 🏓 Bot response latency\n"
        "`/stats` — 📊 Bot statistics\n"
        "`/about` — 🎶 About Melody\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ),
    "admin": (
        "👑 **Admin Commands** _(Group Admins Only)_\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "`/auth [user]` — ✅ Authorize a user\n"
        "`/unauth [user]` — ❌ Remove authorization\n"
        "`/authlist` — 📋 View authorized users\n"
        "`/ban [user]` — 🔨 Ban user from bot\n"
        "`/unban [user]` — ✅ Unban a user\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "_Owner commands are hidden from this menu._"
    ),
}

HELP_MAIN = (
    "📖 **MELODY — Help Menu**\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Welcome! Choose a category to see available commands:\n\n"
    "🎵 **Music** — Play, queue, skip, controls\n"
    "⚙️ **Settings** — Volume, loop, speed, autoplay\n"
    "ℹ️ **Info** — Search, lyrics, ping, stats\n"
    "👑 **Admin** — Auth, ban management\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"_Tip: Use `/play song name` to start instantly!_"
)

# ─── Keyboard builders ────────────────────────────────────────────────────────

def main_help_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵  Music", callback_data="help_music"),
            InlineKeyboardButton("⚙️  Settings", callback_data="help_settings"),
        ],
        [
            InlineKeyboardButton("ℹ️  Info", callback_data="help_info"),
            InlineKeyboardButton("👑  Admin", callback_data="help_admin"),
        ],
        [
            InlineKeyboardButton(
                "➕  Add to Group",
                url=f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}?startgroup=true",
            ),
        ],
    ])


def category_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵  Music", callback_data="help_music"),
            InlineKeyboardButton("⚙️  Settings", callback_data="help_settings"),
        ],
        [
            InlineKeyboardButton("ℹ️  Info", callback_data="help_info"),
            InlineKeyboardButton("👑  Admin", callback_data="help_admin"),
        ],
        [
            InlineKeyboardButton("🏠  Home", callback_data="help_main"),
        ],
    ])


# ─── Handlers ─────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("help"))
@error_handler
async def help_cmd(client: Client, message: Message):
    await message.reply(HELP_MAIN, reply_markup=main_help_kb())


@bot.on_callback_query(filters.regex(r"^help_(.+)$"))
@error_handler
async def help_cb(client: Client, cb: CallbackQuery):
    key = cb.data.split("help_")[1]
    if key == "main":
        await cb.message.edit_text(HELP_MAIN, reply_markup=main_help_kb())
    elif key in HELP_TEXT:
        await cb.message.edit_text(HELP_TEXT[key], reply_markup=category_kb())
    await cb.answer()
