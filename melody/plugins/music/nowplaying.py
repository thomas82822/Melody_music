"""
📊 /np — Now Playing
"""
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from melody import bot
from melody.core.queue import get_current, peek_predownloaded
from utils.decorators import error_handler
from utils.formatters import format_duration, quote_html


@bot.on_message(filters.command("np") & filters.group)
@error_handler
async def nowplaying_cmd(client: Client, message: Message):
    track = get_current(message.chat.id)
    if not track:
        await message.reply(quote_html("❌ Nothing is playing right now."), parse_mode=enums.ParseMode.HTML)
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

    await message.reply(quote_html(text), parse_mode=enums.ParseMode.HTML)
