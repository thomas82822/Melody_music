"""
🔊 Volume commands
BUG FIX: @error_handler moved OUTSIDE @admin_or_auth
"""
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from melody import bot
from melody.core.call import change_volume
from melody.core.queue import get_volume
from utils.decorators import admin_or_auth, error_handler
from utils.formatters import quote_html


@bot.on_message(filters.command("volume") & filters.group)
@error_handler
@admin_or_auth
async def volume_cmd(client: Client, message: Message):
    args = message.command
    if len(args) < 2 or not args[1].isdigit():
        vol = get_volume(message.chat.id)
        await message.reply(
            quote_html(f"🔊 **Current Volume:** `{vol}/200`\n\n**Usage:** `/volume <1-200>`"),
            parse_mode=enums.ParseMode.HTML,
        )
        return
    vol = int(args[1])
    if not (1 <= vol <= 200):
        await message.reply(
            quote_html("❌ Volume must be between 1 and 200."), parse_mode=enums.ParseMode.HTML
        )
        return
    ok = await change_volume(message.chat.id, vol)
    # BUG FIX: this used to always reply "Volume set" even when the
    # underlying Telegram call rejected the change (e.g. GROUPCALL_FORBIDDEN
    # because the assistant isn't currently in the voice chat) — a silent
    # failure disguised as success. Now the reply reflects what actually
    # happened.
    if ok:
        await message.reply(quote_html(f"🔊 **Volume set to** `{vol}`"), parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply(
            quote_html(
                "⚠️ **Volume change nahi ho paya.**\n\n"
                "Voice chat me assistant ka connection issue lag raha hai. "
                "Please `/play` dobara try karo — usse assistant voice chat "
                "me phir se properly join ho jayega."
            ),
            parse_mode=enums.ParseMode.HTML,
        )


@bot.on_message(filters.command("mute") & filters.group)
@error_handler
@admin_or_auth
async def mute_cmd(client: Client, message: Message):
    ok = await change_volume(message.chat.id, 0)
    if ok:
        await message.reply(quote_html("🔇 **Muted.**"), parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply(
            quote_html("⚠️ **Mute nahi ho paya.** Voice chat me assistant ka connection issue lag raha hai — `/play` dobara try karo."),
            parse_mode=enums.ParseMode.HTML,
        )


@bot.on_message(filters.command("unmute") & filters.group)
@error_handler
@admin_or_auth
async def unmute_cmd(client: Client, message: Message):
    ok = await change_volume(message.chat.id, 100)
    if ok:
        await message.reply(quote_html("🔊 **Unmuted.** Volume set to 100."), parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply(
            quote_html("⚠️ **Unmute nahi ho paya.** Voice chat me assistant ka connection issue lag raha hai — `/play` dobara try karo."),
            parse_mode=enums.ParseMode.HTML,
        )
