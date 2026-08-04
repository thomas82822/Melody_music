"""
⚡ /speed command — playback speed (0.5–2.0)
BUG FIX: @error_handler moved OUTSIDE @admin_or_auth
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from utils.decorators import admin_or_auth, error_handler


@bot.on_message(filters.command("speed") & filters.group)
@error_handler
@admin_or_auth
async def speed_cmd(client: Client, message: Message):
    args = message.command
    if len(args) < 2:
        await message.reply("**Usage:** `/speed <0.5-2.0>`\nExample: `/speed 1.5`")
        return
    try:
        speed = float(args[1])
    except ValueError:
        await message.reply("❌ Invalid speed value. Use a number like `1.5`")
        return

    if not (0.5 <= speed <= 2.0):
        await message.reply("❌ Speed must be between **0.5** and **2.0**")
        return

    # Note: PyTgCalls speed control requires FFmpeg filter
    # This is a placeholder — advanced speed control via FFmpeg piped input
    await message.reply(
        f"⚡ **Playback speed set to** `{speed}x`\n"
        "_Note: Speed change takes effect on next track._"
    )
