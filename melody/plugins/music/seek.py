"""
⏩ Seek and rewind commands
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.core.call import seek_stream
from utils.decorators import admin_or_auth, error_handler


@bot.on_message(filters.command("seek") & filters.group)
@admin_or_auth
@error_handler
async def seek_cmd(client: Client, message: Message):
    args = message.command
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("**Usage:** `/seek <seconds>`")
        return
    seconds = int(args[1])
    await seek_stream(message.chat.id, seconds)
    await message.reply(f"⏩ Seeked to `{seconds}s`")


@bot.on_message(filters.command("rewind") & filters.group)
@admin_or_auth
@error_handler
async def rewind_cmd(client: Client, message: Message):
    args = message.command
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("**Usage:** `/rewind <seconds>`")
        return
    seconds = int(args[1])
    await seek_stream(message.chat.id, -seconds)
    await message.reply(f"⏪ Rewound by `{seconds}s`")
