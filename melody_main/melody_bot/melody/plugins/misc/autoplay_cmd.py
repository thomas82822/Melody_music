"""
🤖 /autoplay command
BUG FIX: @error_handler moved OUTSIDE @admin_or_auth
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.core.queue import set_autoplay, is_autoplay_on
from utils.decorators import admin_or_auth, error_handler


@bot.on_message(filters.command("autoplay") & filters.group)
@error_handler
@admin_or_auth
async def autoplay_cmd(client: Client, message: Message):
    args = message.command
    if len(args) < 2:
        status = await is_autoplay_on(message.chat.id)
        state = "ON 🟢" if status else "OFF 🔴"
        await message.reply(
            f"🤖 **AutoPlay:** {state}\n\n"
            "Use `/autoplay on` or `/autoplay off` to toggle."
        )
        return

    arg = args[1].lower()
    if arg == "on":
        await set_autoplay(message.chat.id, True)
        await message.reply("🤖 **AutoPlay enabled.** Melody will play related songs when queue is empty.")
    elif arg == "off":
        await set_autoplay(message.chat.id, False)
        await message.reply("🤖 **AutoPlay disabled.**")
    else:
        await message.reply("**Usage:** `/autoplay on` or `/autoplay off`")
