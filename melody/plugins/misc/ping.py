"""
🏓 /ping — latency check with HTML blockquote formatting
"""
import time
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from melody import bot
from utils.decorators import error_handler


@bot.on_message(filters.command("ping"))
@error_handler
async def ping_cmd(client: Client, message: Message):
    start = time.monotonic()
    msg = await message.reply(
        "<blockquote>🏓 <b>Pinging...</b></blockquote>",
        parse_mode=enums.ParseMode.HTML,
    )
    elapsed = (time.monotonic() - start) * 1000
    await msg.edit_text(
        "<blockquote>🏓 <b>Pong!</b></blockquote>\n\n"
        f"⚡ <b>Response:</b> <code>{elapsed:.2f}ms</code>\n"
        f"<i>Bot is alive and kicking! 🎶</i>",
        parse_mode=enums.ParseMode.HTML,
    )
