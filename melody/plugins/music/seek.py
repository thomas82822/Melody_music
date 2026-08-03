"""
⏩ Seek and rewind commands
BUG FIX: @error_handler moved OUTSIDE @admin_or_auth
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.core.call import seek_stream
from melody.core.queue import get_current
from utils.decorators import admin_or_auth, error_handler


@bot.on_message(filters.command("seek") & filters.group)
@error_handler
@admin_or_auth
async def seek_cmd(client: Client, message: Message):
    args = message.command
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("**Usage:** `/seek <seconds>`\nExample: `/seek 60` → jump to 1 minute")
        return
    seconds = int(args[1])
    if seconds < 0:
        await message.reply("❌ Seek value must be a positive number of seconds.")
        return
    track = get_current(message.chat.id)
    if not track:
        await message.reply("❌ Nothing is playing right now.")
        return
    if seconds > track.duration:
        await message.reply(f"❌ Cannot seek past track duration ({track.duration}s).")
        return
    await seek_stream(message.chat.id, seconds)
    await message.reply(f"⏩ Seeked to `{seconds}s`")


@bot.on_message(filters.command("rewind") & filters.group)
@error_handler
@admin_or_auth
async def rewind_cmd(client: Client, message: Message):
    await message.reply(
        "⚠️ **Rewind is not supported** by the voice call engine.\n"
        "Use `/seek <seconds>` to jump to a specific position instead."
    )
