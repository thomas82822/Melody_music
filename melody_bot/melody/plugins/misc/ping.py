"""
🏓 /ping — latency check
"""
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from utils.decorators import error_handler


@bot.on_message(filters.command("ping"))
@error_handler
async def ping_cmd(client: Client, message: Message):
    start = time.monotonic()
    msg = await message.reply("🏓 Pinging...")
    elapsed = (time.monotonic() - start) * 1000
    await msg.edit(f"🏓 **Pong!** `{elapsed:.2f}ms`")
