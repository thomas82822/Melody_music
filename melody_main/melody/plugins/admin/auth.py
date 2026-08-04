"""
👑 Auth management — authorize/unauthorize users in groups
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from utils.database import auth_user, unauth_user, get_auth_users
from utils.decorators import error_handler


@bot.on_message(filters.command("auth") & filters.group)
@error_handler
async def auth_cmd(client: Client, message: Message):
    # Only group admins or creator
    if not await _is_admin(client, message):
        return await message.reply("⚠️ Admins only.")

    user = await _get_target_user(message)
    if not user:
        return await message.reply("**Usage:** `/auth @user` or reply to a user")

    await auth_user(message.chat.id, user.id)
    await message.reply(f"✅ {user.mention} authorized to use bot commands.")


@bot.on_message(filters.command("unauth") & filters.group)
@error_handler
async def unauth_cmd(client: Client, message: Message):
    if not await _is_admin(client, message):
        return await message.reply("⚠️ Admins only.")

    user = await _get_target_user(message)
    if not user:
        return await message.reply("**Usage:** `/unauth @user` or reply to a user")

    await unauth_user(message.chat.id, user.id)
    await message.reply(f"🚫 {user.mention} unauthorized.")


@bot.on_message(filters.command("authlist") & filters.group)
@error_handler
async def authlist_cmd(client: Client, message: Message):
    auth_ids = await get_auth_users(message.chat.id)
    if not auth_ids:
        return await message.reply("📋 No authorized users in this group.")

    lines = ["**📋 Authorized Users:**\n"]
    for uid in auth_ids:
        try:
            user = await client.get_users(uid)
            lines.append(f"• {user.mention} (`{uid}`)")
        except Exception:
            lines.append(f"• `{uid}`")
    await message.reply("\n".join(lines))


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
