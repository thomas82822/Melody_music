"""
🎛 Playback controls — pause, resume, skip, stop
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.core.call import pause_stream, resume_stream, skip_stream, stop_stream
from utils.decorators import admin_or_auth, error_handler


@bot.on_message(filters.command("pause") & filters.group)
@admin_or_auth
@error_handler
async def pause_cmd(client: Client, message: Message):
    await pause_stream(message.chat.id)
    await message.reply("⏸ **Paused.**")


@bot.on_message(filters.command("resume") & filters.group)
@admin_or_auth
@error_handler
async def resume_cmd(client: Client, message: Message):
    await resume_stream(message.chat.id)
    await message.reply("▶️ **Resumed.**")


@bot.on_message(filters.command(["skip", "s"]) & filters.group)
@admin_or_auth
@error_handler
async def skip_cmd(client: Client, message: Message):
    await skip_stream(message.chat.id)
    await message.reply("⏭ **Skipped.**")


@bot.on_message(filters.command("stop") & filters.group)
@admin_or_auth
@error_handler
async def stop_cmd(client: Client, message: Message):
    await stop_stream(message.chat.id)
    await message.reply("⏹ **Music stopped and queue cleared.**")
