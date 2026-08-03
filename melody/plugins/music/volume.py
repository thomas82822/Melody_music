"""
🔊 Volume commands
BUG FIX: @error_handler moved OUTSIDE @admin_or_auth
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.core.call import change_volume
from melody.core.queue import get_volume
from utils.decorators import admin_or_auth, error_handler


@bot.on_message(filters.command("volume") & filters.group)
@error_handler
@admin_or_auth
async def volume_cmd(client: Client, message: Message):
    args = message.command
    if len(args) < 2 or not args[1].isdigit():
        vol = get_volume(message.chat.id)
        await message.reply(f"🔊 **Current Volume:** `{vol}/200`\n\n**Usage:** `/volume <1-200>`")
        return
    vol = int(args[1])
    if not (1 <= vol <= 200):
        await message.reply("❌ Volume must be between 1 and 200.")
        return
    await change_volume(message.chat.id, vol)
    await message.reply(f"🔊 **Volume set to** `{vol}`")


@bot.on_message(filters.command("mute") & filters.group)
@error_handler
@admin_or_auth
async def mute_cmd(client: Client, message: Message):
    await change_volume(message.chat.id, 0)
    await message.reply("🔇 **Muted.**")


@bot.on_message(filters.command("unmute") & filters.group)
@error_handler
@admin_or_auth
async def unmute_cmd(client: Client, message: Message):
    await change_volume(message.chat.id, 100)
    await message.reply("🔊 **Unmuted.** Volume set to 100.")
