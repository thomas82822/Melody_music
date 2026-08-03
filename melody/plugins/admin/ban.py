"""
🚫 Ban/unban users from the bot
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.config import Config
from utils.database import ban_user, unban_user, is_banned
from utils.decorators import owner_only, error_handler


@bot.on_message(filters.command("ban") & filters.group)
@error_handler
async def ban_cmd(client: Client, message: Message):
    if not await _is_admin(client, message):
        return await message.reply("⚠️ Admins only.")

    user = await _get_target_user(message)
    if not user:
        return await message.reply("**Usage:** `/ban @user` or reply to user")

    if user.id == Config.OWNER_ID:
        return await message.reply("❌ Cannot ban the owner.")

    reason = " ".join(message.command[2:]) if len(message.command) > 2 else ""
    await ban_user(user.id, reason)
    await message.reply(f"🚫 {user.mention} banned from using the bot.")


@bot.on_message(filters.command("unban") & filters.group)
@error_handler
async def unban_cmd(client: Client, message: Message):
    if not await _is_admin(client, message):
        return await message.reply("⚠️ Admins only.")

    user = await _get_target_user(message)
    if not user:
        return await message.reply("**Usage:** `/unban @user` or reply to user")

    await unban_user(user.id)
    await message.reply(f"✅ {user.mention} unbanned.")


async def _is_admin(client: Client, message: Message) -> bool:
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def _get_target_user(message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    if len(message.command) > 1:
        try:
            return await message._client.get_users(message.command[1])
        except Exception:
            pass
    return None
