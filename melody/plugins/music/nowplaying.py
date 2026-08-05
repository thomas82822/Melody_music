"""
📊 /np — Now Playing
"""
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from melody import bot
from melody.core.queue import get_current, peek_predownloaded
from utils.decorators import error_handler
from utils.formatters import format_duration, send_quote


@bot.on_message(filters.command("np") & filters.group)
@error_handler
async def nowplaying_cmd(client: Client, message: Message):
    track = get_current(message.chat.id)
    if not track:
        await send_quote(message, "❌ Nothing is playing right now.", client=client)
        return

    text = (
        f"🎵 **Now Playing**\n\n"
        f"**{track.title[:50]}**\n"
        f"👤 `{track.uploader}`\n"
        f"⏱ `{format_duration(track.duration)}`\n"
        f"🙋 Requested by `{track.requester_name}`"
    )

    up_next = peek_predownloaded(message.chat.id)
    if up_next:
        text += (
            f"\n\n🤖 **Up Next (AutoPlay):**\n"
            f"`{up_next.title[:45]}`\n"
            f"🙋 Requested by `AutoPlay`"
        )

    await send_quote(message, text, client=client)
