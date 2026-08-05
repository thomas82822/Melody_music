"""
🔁 Loop commands
BUG FIX: @error_handler moved OUTSIDE @admin_or_auth
"""
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from melody import bot
from melody.core.queue import set_loop, get_loop
from utils.decorators import admin_or_auth, error_handler
from utils.formatters import quote_html


@bot.on_message(filters.command("loop") & filters.group)
@error_handler
@admin_or_auth
async def loop_cmd(client: Client, message: Message):
    set_loop(message.chat.id, "single")
    await message.reply(quote_html("🔂 **Looping current song.**"), parse_mode=enums.ParseMode.HTML)


@bot.on_message(filters.command("loopall") & filters.group)
@error_handler
@admin_or_auth
async def loopall_cmd(client: Client, message: Message):
    set_loop(message.chat.id, "all")
    await message.reply(quote_html("🔁 **Looping entire queue.**"), parse_mode=enums.ParseMode.HTML)


@bot.on_message(filters.command("noloop") & filters.group)
@error_handler
@admin_or_auth
async def noloop_cmd(client: Client, message: Message):
    set_loop(message.chat.id, "none")
    await message.reply(quote_html("▶️ **Loop disabled.**"), parse_mode=enums.ParseMode.HTML)
