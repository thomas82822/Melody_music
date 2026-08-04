"""
🔁 /restart — restart bot (owner only)
"""
import asyncio
import os
import sys
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from utils.decorators import owner_only, error_handler


@bot.on_message(filters.command("restart") & filters.private)
@owner_only
@error_handler
async def restart_cmd(client: Client, message: Message):
    await message.reply("🔁 Restarting Melody...")
    await asyncio.sleep(1)
    os.execv(sys.executable, [sys.executable, "-m", "melody"])
