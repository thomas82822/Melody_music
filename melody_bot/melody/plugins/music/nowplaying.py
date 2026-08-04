"""
📊 /np — Now Playing
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.core.queue import get_current
from utils.decorators import error_handler
from utils.formatters import format_duration


@bot.on_message(filters.command("np") & filters.group)
@error_handler
async def nowplaying_cmd(client: Client, message: Message):
    track = get_current(message.chat.id)
    if not track:
        await message.reply("❌ Nothing is playing right now.")
        return

    text = (
        f"🎵 **Now Playing**\n\n"
        f"**{track.title[:50]}**\n"
        f"👤 `{track.uploader}`\n"
        f"⏱ `{format_duration(track.duration)}`\n"
        f"🙋 Requested by `{track.requester_name}`"
    )
    await message.reply(text)
