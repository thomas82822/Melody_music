"""
🔁 Loop commands
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.core.queue import set_loop, get_loop
from utils.decorators import admin_or_auth, error_handler


@bot.on_message(filters.command("loop") & filters.group)
@admin_or_auth
@error_handler
async def loop_cmd(client: Client, message: Message):
    set_loop(message.chat.id, "single")
    await message.reply("🔂 **Looping current song.**")


@bot.on_message(filters.command("loopall") & filters.group)
@admin_or_auth
@error_handler
async def loopall_cmd(client: Client, message: Message):
    set_loop(message.chat.id, "all")
    await message.reply("🔁 **Looping entire queue.**")


@bot.on_message(filters.command("noloop") & filters.group)
@admin_or_auth
@error_handler
async def noloop_cmd(client: Client, message: Message):
    set_loop(message.chat.id, "none")
    await message.reply("▶️ **Loop disabled.**")
