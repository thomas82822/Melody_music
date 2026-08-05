"""
🏓 /ping — latency check with HTML blockquote formatting
"""
import time
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from melody import bot
from utils.decorators import error_handler
from utils.formatters import send_quote


@bot.on_message(filters.command("ping"))
@error_handler
async def ping_cmd(client: Client, message: Message):
    start = time.monotonic()
    msg = await send_quote(message, "🏓 <b>Pinging...</b>", client=client)
    elapsed = (time.monotonic() - start) * 1000
    await send_quote(
        msg,
        "🏓 <b>Pong!</b>\n\n"
        f"⚡ <b>Response:</b> <code>{elapsed:.2f}ms</code>\n"
        f"<i>Bot is alive and kicking! 🎶</i>",
        client=client,
        edit=True,
    )
