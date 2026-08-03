"""
▶️ /play and /vplay commands
"""
import urllib.parse
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from melody import bot
from melody.config import Config
from melody.core.ytdl import get_video_info
from melody.core.queue import Track, add_to_queue
from melody.core.call import play_stream
from utils.database import add_history
from utils.decorators import admin_or_auth, error_handler
from utils.formatters import format_duration
from utils.thumbnails import make_thumbnail


def get_play_buttons(chat_title: str) -> InlineKeyboardMarkup:
    encoded_title = urllib.parse.quote(chat_title[:30])
    webapp_url = f"{Config.WEBAPP_URL}?chat={encoded_title}"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Pause",  callback_data="pause"),
            InlineKeyboardButton("⏭ Skip",   callback_data="skip"),
            InlineKeyboardButton("⏹ Stop",   callback_data="stop"),
        ],
        [
            InlineKeyboardButton("🎛 Colored Controls", web_app=WebAppInfo(url=webapp_url)),
        ],
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

    playing_now = await play_stream(chat.id, track, video=video)
    await add_history(chat.id, info["id"], info["title"])

    # Generate thumbnail
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
            f"🎶 **{'Now Playing' if playing_now else 'Added to Queue'}**\n\n"
            f"**{info['title'][:50]}**\n"
            f"👤 `{info['uploader']}`  ⏱ `{format_duration(info['duration'])}`\n"
            f"🙋 Requested by {user.mention}"
        )
        await processing.delete()
        await message.reply_photo(
            thumb_path,
            caption=caption,
            reply_markup=get_play_buttons(chat.title or ""),
        )
    except Exception:
        status = "Now Playing ▶️" if playing_now else "Added to Queue 📋"
        await processing.edit(
            f"🎵 **{status}**\n\n`{info['title'][:50]}`\n👤 `{info['uploader']}`  ⏱ `{format_duration(info['duration'])}`",
            reply_markup=get_play_buttons(chat.title or ""),
        )


@bot.on_message(filters.command("play") & filters.group)
@admin_or_auth
@error_handler
async def play_cmd(client: Client, message: Message):
    await _play_core(client, message, video=False)


@bot.on_message(filters.command("vplay") & filters.group)
@admin_or_auth
@error_handler
async def vplay_cmd(client: Client, message: Message):
    await _play_core(client, message, video=True)


# ─── Callback query handlers ──────────────────────────────────────────────────

@bot.on_callback_query(filters.regex("^pause$"))
async def cb_pause(client, cb):
    from melody.core.call import pause_stream
    await pause_stream(cb.message.chat.id)
    await cb.answer("⏸ Paused")


@bot.on_callback_query(filters.regex("^resume$"))
async def cb_resume(client, cb):
    from melody.core.call import resume_stream
    await resume_stream(cb.message.chat.id)
    await cb.answer("▶️ Resumed")


@bot.on_callback_query(filters.regex("^skip$"))
async def cb_skip(client, cb):
    from melody.core.call import skip_stream
    await skip_stream(cb.message.chat.id)
    await cb.answer("⏭ Skipped")


@bot.on_callback_query(filters.regex("^stop$"))
async def cb_stop(client, cb):
    from melody.core.call import stop_stream
    await stop_stream(cb.message.chat.id)
    await cb.answer("⏹ Stopped")
    await cb.message.reply("⏹ **Music stopped and queue cleared.**")


@bot.on_callback_query(filters.regex("^queue$"))
async def cb_queue(client, cb):
    from melody.core.queue import format_queue
    text = format_queue(cb.message.chat.id)
    await cb.answer()
    await cb.message.reply(text)


@bot.on_callback_query(filters.regex("^lyrics$"))
async def cb_lyrics(client, cb):
    from melody.core.queue import get_current
    track = get_current(cb.message.chat.id)
    if track:
        await cb.answer()
        await cb.message.reply(f"🔍 Searching lyrics for: `{track.title}`...")
        # Lyrics fetched by lyrics plugin
    else:
        await cb.answer("Nothing is playing!", show_alert=True)
