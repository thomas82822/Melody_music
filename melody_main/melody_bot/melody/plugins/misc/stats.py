"""
📊 /stats — bot statistics
"""
import psutil
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from utils.database import get_stats
from utils.decorators import error_handler

_start_time = time.time()


@bot.on_message(filters.command("stats"))
@error_handler
async def stats_cmd(client: Client, message: Message):
    db_stats = await get_stats()
    uptime_sec = int(time.time() - _start_time)
    hours = uptime_sec // 3600
    minutes = (uptime_sec % 3600) // 60
    secs = uptime_sec % 60

    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()

    text = (
        "📊 **Melody Statistics**\n\n"
        f"🕒 **Uptime:** `{hours}h {minutes}m {secs}s`\n"
        f"💻 **CPU:** `{cpu}%`\n"
        f"🧠 **RAM:** `{ram.percent}%` ({ram.used // 1024 // 1024}MB / {ram.total // 1024 // 1024}MB)\n\n"
        f"🏛 **Total Chats:** `{db_stats['chats']}`\n"
        f"🚫 **Banned Users:** `{db_stats['banned']}`\n"
        f"🌐 **Globally Banned:** `{db_stats['gbanned']}`\n"
    )
    await message.reply(text)
