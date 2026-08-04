"""
📋 Queue commands
BUG FIX: @error_handler moved OUTSIDE @admin_or_auth
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.core.queue import format_queue, clear_queue, remove_from_queue
from utils.decorators import admin_or_auth, error_handler


@bot.on_message(filters.command(["queue", "q"]) & filters.group)
@error_handler
async def queue_cmd(client: Client, message: Message):
    text = format_queue(message.chat.id)
    await message.reply(text)


@bot.on_message(filters.command("clearqueue") & filters.group)
@error_handler
@admin_or_auth
async def clearqueue_cmd(client: Client, message: Message):
    clear_queue(message.chat.id)
    await message.reply("🗑 **Queue cleared.**")


@bot.on_message(filters.command("remove") & filters.group)
@error_handler
@admin_or_auth
async def remove_cmd(client: Client, message: Message):
    args = message.command
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("**Usage:** `/remove <position>`")
        return
    pos = int(args[1])
    removed = remove_from_queue(message.chat.id, pos)
    if removed:
        await message.reply(f"🗑 Removed: `{removed.title[:40]}`")
    else:
        await message.reply("❌ Invalid position.")
