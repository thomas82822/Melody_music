"""
▶️ /play and /vplay commands
BUG FIX: @error_handler moved OUTSIDE @admin_or_auth so DB errors are also caught
BUG FIX: Removed duplicate callback handlers (pause/resume/skip/stop/queue/lyrics
         are already registered in controls.py — having them here too caused
         duplicate handler registration and unpredictable behaviour)
BUG FIX: ENTITY_BOUNDS_INVALID — switched all dynamic-text messages to HTML
         parse_mode with html.escape() so song titles / uploader names that
         contain Markdown special characters (* _ ` [ etc.) never produce
         malformed entities.  Slicing a title string mid-Markdown-token was
         the direct trigger for [400 ENTITY_BOUNDS_INVALID].
"""
import html
import urllib.parse
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from melody import bot
from melody.config import Config
from melody.core.ytdl import get_video_info
from melody.core.queue import Track, add_to_queue
from melody.core.call import play_stream
from utils.database import add_history, add_chat
from utils.decorators import admin_or_auth, error_handler
from utils.formatters import format_duration
from utils.thumbnails import make_thumbnail


def get_play_buttons(chat_title: str) -> InlineKeyboardMarkup:
    encoded_title = urllib.parse.quote(chat_title[:30])
    webapp_url = f"{Config.WEBAPP_URL}?chat={encoded_title}" if Config.WEBAPP_URL else "https://t.me"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Pause",  callback_data="pause"),
            InlineKeyboardButton("⏭ Skip",   callback_data="skip"),
            InlineKeyboardButton("⏹ Stop",   callback_data="stop"),
        ],
        [
            InlineKeyboardButton("🎛 Colored Controls", web_app=WebAppInfo(url=webapp_url)),
        ] if Config.WEBAPP_URL else [],
        [
            InlineKeyboardButton("📋 Queue",  callback_data="queue"),
            InlineKeyboardButton("🎵 Lyrics", callback_data="lyrics"),
        ],
    ])


async def _play_core(client: Client, message: Message, video: bool = False):
    query = " ".join(message.command[1:]) if len(message.command) > 1 else None
    if not query:
        await message.reply("**Usage:** `/play <song name or YouTube URL>`")
        return

    processing = await message.reply("🔍 Searching...")

    info = await get_video_info(query)
    if not info:
        await processing.edit("❌ Song nahi mili 🌸")
        return

    if info["duration"] > Config.MAX_DURATION:
        await processing.edit(f"⚠️ Song too long! Max allowed: {format_duration(Config.MAX_DURATION)}")
        return

    chat = message.chat
    user = message.from_user

    track = Track(
        video_id=info["id"],
        title=info["title"],
        duration=info["duration"],
        stream_url=info["stream_url"],
        thumbnail=info["thumbnail"],
        uploader=info["uploader"],
        requester_id=user.id,
        requester_name=user.first_name,
        requested_in=chat.id,
    )

    # Save chat to DB on every /play so warm_bot_peer_cache works correctly.
    # new_group_handler only fires when bot is first ADDED — existing groups
    # that were added before this code was deployed are never stored otherwise.
    await add_chat(chat.id, chat.title or "")

    playing_now = await play_stream(chat.id, track, video=video)
    await add_history(chat.id, info["id"], info["title"])

    # Generate thumbnail
    # NOTE: all dynamic text (title, uploader, requester name) is passed through
    # html.escape() to prevent ENTITY_BOUNDS_INVALID.  We use parse_mode="html"
    # so Pyrogram does NOT try to parse Markdown tokens inside the escaped text.
    status_label = "Now Playing" if playing_now else "Added to Queue"
    safe_title    = html.escape(info["title"][:50])
    safe_uploader = html.escape(info["uploader"])
    safe_duration = html.escape(format_duration(info["duration"]))

    try:
        thumb_path = await make_thumbnail(
            song_title=info["title"],
            artist=info["uploader"],
            duration=format_duration(info["duration"]),
            requester_name=user.first_name,
            group_name=chat.title or "Private",
            owner_name=Config.OWNER_NAME,
            yt_thumbnail_url=info["thumbnail"],
        )
        caption = (
            f"🎶 <b>{html.escape(status_label)}</b>\n\n"
            f"<b>{safe_title}</b>\n"
            f"👤 <code>{safe_uploader}</code>  ⏱ <code>{safe_duration}</code>\n"
            f"🙋 Requested by {user.mention}"
        )
        await processing.delete()
        await message.reply_photo(
            thumb_path,
            caption=caption,
            parse_mode="html",
            reply_markup=get_play_buttons(chat.title or ""),
        )
    except Exception:
        status = "Now Playing ▶️" if playing_now else "Added to Queue 📋"
        await processing.edit(
            f"🎵 <b>{html.escape(status)}</b>\n\n"
            f"<code>{safe_title}</code>\n"
            f"👤 <code>{safe_uploader}</code>  ⏱ <code>{safe_duration}</code>",
            parse_mode="html",
            reply_markup=get_play_buttons(chat.title or ""),
        )


# BUG FIX: @error_handler is OUTER decorator — catches errors from admin_or_auth too
@bot.on_message(filters.command("play") & filters.group)
@error_handler
@admin_or_auth
async def play_cmd(client: Client, message: Message):
    await _play_core(client, message, video=False)


@bot.on_message(filters.command("vplay") & filters.group)
@error_handler
@admin_or_auth
async def vplay_cmd(client: Client, message: Message):
    await _play_core(client, message, video=True)
