"""
🔍 /search command — inline YouTube search results
"""
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from melody import bot
from melody.core.ytdl import search_youtube
from utils.decorators import error_handler
from utils.formatters import format_duration
from strings.themes import RED, btn


@bot.on_message(filters.command("search") & filters.group)
@error_handler
async def search_cmd(client: Client, message: Message):
    query = " ".join(message.command[1:])
    if not query:
        await message.reply("**Usage:** `/search <song name>`")
        return

    msg = await message.reply("🔍 Searching YouTube...")
    results = await search_youtube(query, limit=5)

    if not results:
        await msg.edit("❌ No results found.")
        return

    text = "**🔍 Search Results:**\n\n"
    buttons = []
    for i, r in enumerate(results[:5], 1):
        dur = format_duration(r["duration"]) if r["duration"] else "?"
        text += f"`{i}.` **{r['title'][:45]}**\n   👤 {r['uploader']}  ⏱ {dur}\n\n"
        buttons.append([
            InlineKeyboardButton(
                btn(f"{i}. {r['title'][:30]}", RED),
                callback_data=f"play_search_{r['id']}"
            )
        ])

    await msg.edit(text, reply_markup=InlineKeyboardMarkup(buttons))


@bot.on_callback_query(filters.regex(r"^play_search_(.+)$"))
async def play_search_cb(client, cb):
    from melody.core.ytdl import get_video_info
    from melody.core.queue import Track, add_to_queue
    from melody.core.call import play_stream
    from melody.config import Config
    from utils.formatters import format_duration
    from utils.database import add_history

    video_id = cb.data.split("play_search_")[1]
    await cb.answer("🎵 Loading...")

    info = await get_video_info(f"https://www.youtube.com/watch?v={video_id}")
    if not info:
        await cb.answer("❌ Could not load song.", show_alert=True)
        return

    user = cb.from_user
    chat = cb.message.chat

    if info["duration"] > Config.MAX_DURATION:
        await cb.answer("⚠️ Song too long!", show_alert=True)
        return

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

    playing = await play_stream(chat.id, track)
    await add_history(chat.id, info["id"], info["title"])

    status = "▶️ Now Playing" if playing else "📋 Added to Queue"
    await cb.message.reply(
        f"🎵 **{status}**\n`{info['title'][:50]}`\n⏱ `{format_duration(info['duration'])}`"
    )
