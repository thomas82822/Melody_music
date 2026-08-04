"""
🔄 /update — git pull + restart (owner only)
"""
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from utils.decorators import owner_only, error_handler


@bot.on_message(filters.command("update") & filters.private)
@owner_only
@error_handler
async def update_cmd(client: Client, message: Message):
    msg = await message.reply("🔄 Pulling latest changes...")
    proc = await asyncio.create_subprocess_shell(
        "git pull origin main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = stdout.decode() + stderr.decode()
    await msg.edit(f"**Git Pull:**\n```\n{output[:1000]}\n```\n\n🔁 Restarting...")

    await asyncio.sleep(2)
    import os, sys
    os.execv(sys.executable, [sys.executable, "-m", "melody"])
