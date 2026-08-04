"""
🌐 Global ban — owner only
BUG FIX: @error_handler moved OUTSIDE @owner_only so errors are caught and
logged instead of failing silently for the owner.
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.config import Config
from utils.database import gban_user, ungban_user, is_gbanned
from utils.decorators import owner_only, error_handler


@bot.on_message(filters.command("gban") & filters.private)
@error_handler
@owner_only
async def gban_cmd(client: Client, message: Message):
    user = await _get_target_user(message)
    if not user:
        return await message.reply("**Usage:** `/gban @user` or reply to user")

    if user.id == Config.OWNER_ID:
        return await message.reply("❌ Cannot gban yourself.")

    reason = " ".join(message.command[2:]) if len(message.command) > 2 else ""
    await gban_user(user.id, reason)
    await message.reply(f"🌐 `{user.id}` globally banned.")


@bot.on_message(filters.command("ungban") & filters.private)
@error_handler
@owner_only
async def ungban_cmd(client: Client, message: Message):
    user = await _get_target_user(message)
    if not user:
        return await message.reply("**Usage:** `/ungban @user` or reply to user")

    await ungban_user(user.id)
    await message.reply(f"✅ `{user.id}` removed from global ban.")


async def _get_target_user(message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    if len(message.command) > 1:
        try:
            return await message._client.get_users(message.command[1])
        except Exception:
            pass
    return None
