"""
📋 /help command — categorized inline help
"""
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from melody import bot
from melody.config import Config
from utils.decorators import error_handler

HELP_TEXT = {
    "music": (
        "🎵 **Music Commands**\n\n"
        "`/play [song/url]` — Play from YouTube\n"
        "`/vplay [song/url]` — Video stream\n"
        "`/queue` or `/q` — Show queue\n"
        "`/skip` or `/s` — Skip song\n"
        "`/pause` — Pause\n"
        "`/resume` — Resume\n"
        "`/stop` — Stop + clear queue\n"
        "`/seek [sec]` — Seek forward\n"
        "`/rewind [sec]` — Seek backward\n"
        "`/np` — Now playing\n"
        "`/shuffle` — Shuffle queue\n"
        "`/clearqueue` — Clear queue\n"
        "`/remove [pos]` — Remove from queue\n"
    ),
    "settings": (
        "⚙️ **Settings Commands**\n\n"
        "`/volume [1-200]` — Set volume\n"
        "`/mute` — Mute\n"
        "`/unmute` — Unmute\n"
        "`/loop` — Loop current song\n"
        "`/loopall` — Loop queue\n"
        "`/noloop` — Disable loop\n"
        "`/speed [0.5-2.0]` — Playback speed\n"
        "`/autoplay on/off` — Toggle autoplay\n"
    ),
    "info": (
        "ℹ️ **Info Commands**\n\n"
        "`/search [query]` — Search YouTube\n"
        "`/lyrics [song]` — Genius lyrics\n"
        "`/np` — Now playing info\n"
        "`/ping` — Bot latency\n"
        "`/stats` — Bot statistics\n"
        "`/about` — About Melody\n"
    ),
    "admin": (
        "👑 **Admin Commands** _(group admins)_\n\n"
        "`/auth [user]` — Authorize user\n"
        "`/unauth [user]` — Remove auth\n"
        "`/authlist` — Authorized users list\n"
        "`/ban [user]` — Ban from bot\n"
        "`/unban [user]` — Unban\n"
    ),
}


def help_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 Music", callback_data="help_music"),
            InlineKeyboardButton("⚙️ Settings", callback_data="help_settings"),
        ],
        [
            InlineKeyboardButton("ℹ️ Info", callback_data="help_info"),
            InlineKeyboardButton("👑 Admin", callback_data="help_admin"),
        ],
        [
            InlineKeyboardButton("🏠 Back", callback_data="help_main"),
        ],
    ])


def main_help_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 Music", callback_data="help_music"),
            InlineKeyboardButton("⚙️ Settings", callback_data="help_settings"),
        ],
        [
            InlineKeyboardButton("ℹ️ Info", callback_data="help_info"),
            InlineKeyboardButton("👑 Admin", callback_data="help_admin"),
        ],
    ])


@bot.on_message(filters.command("help"))
@error_handler
async def help_cmd(client: Client, message: Message):
    text = (
        "📋 **MELODY — Help Menu**\n\n"
        "Choose a category below to see commands:\n\n"
        "🎵 **Music** — Play, queue, skip\n"
        "⚙️ **Settings** — Volume, loop, speed\n"
        "ℹ️ **Info** — Search, lyrics, stats\n"
        "👑 **Admin** — Auth, ban management\n\n"
        "_Owner commands are hidden from this menu._"
    )
    await message.reply(text, reply_markup=main_help_buttons())


@bot.on_callback_query(filters.regex(r"^help_(.+)$"))
async def help_cb(client: Client, cb: CallbackQuery):
    key = cb.data.split("help_")[1]
    if key == "main":
        text = (
            "📋 **MELODY — Help Menu**\n\n"
            "Choose a category below to see commands:\n\n"
            "🎵 **Music** — Play, queue, skip\n"
            "⚙️ **Settings** — Volume, loop, speed\n"
            "ℹ️ **Info** — Search, lyrics, stats\n"
            "👑 **Admin** — Auth, ban management"
        )
        await cb.message.edit_text(text, reply_markup=main_help_buttons())
    elif key in HELP_TEXT:
        await cb.message.edit_text(HELP_TEXT[key], reply_markup=help_buttons())
    await cb.answer()
