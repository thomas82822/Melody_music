"""
🔀 /shuffle command
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.core.queue import shuffle_queue
from utils.decorators import admin_or_auth, error_handler


@bot.on_message(filters.command("shuffle") & filters.group)
@admin_or_auth
@error_handler
async def shuffle_cmd(client: Client, message: Message):
    shuffle_queue(message.chat.id)
    await message.reply("🔀 **Queue shuffled!**")
