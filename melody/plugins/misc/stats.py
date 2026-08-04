"""
📊 /stats — bot statistics with HTML blockquote formatting
"""
import psutil
import time
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from melody import bot
from utils.database import get_stats
from utils.decorators import error_handler
from strings.themes import fancy

_start_time = time.time()


@bot.on_message(filters.command("stats"))
@error_handler
async def stats_cmd(client: Client, message: Message):
    db_stats = await get_stats()
    uptime_sec = int(time.time() - _start_time)
    hours   = uptime_sec // 3600
    minutes = (uptime_sec % 3600) // 60
    secs    = uptime_sec % 60

    cpu  = psutil.cpu_percent(interval=1)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    text = (
        f"<blockquote>📊 <b>{fancy('Melody Statistics')}</b></blockquote>\n\n"
        "<blockquote>"
        f"🕒 <b>Uptime:</b> <code>{hours}h {minutes}m {secs}s</code>\n\n"
        "💻 <b>System:</b>\n"
        f"  ▸ CPU:  <code>{cpu}%</code>\n"
        f"  ▸ RAM:  <code>{ram.percent}%</code> "
        f"<i>({ram.used // 1024 // 1024}MB / {ram.total // 1024 // 1024}MB)</i>\n"
        f"  ▸ Disk: <code>{disk.percent}%</code> "
        f"<i>({disk.used // 1024 // 1024 // 1024}GB / {disk.total // 1024 // 1024 // 1024}GB)</i>"
        "</blockquote>\n\n"
        "<blockquote>"
        "📈 <b>Database:</b>\n"
        f"  ▸ Total Chats:    <code>{db_stats['chats']}</code>\n"
        f"  ▸ Banned Users:   <code>{db_stats['banned']}</code>\n"
        f"  ▸ Globally Banned: <code>{db_stats['gbanned']}</code>"
        "</blockquote>"
    )
    await message.reply(text, parse_mode=enums.ParseMode.HTML)
