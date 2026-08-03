"""
🔒 Decorators for permission checks
"""
import functools
from pyrogram import Client
from pyrogram.types import Message
from melody.config import Config
from melody.logging import send_error_log
from utils.database import is_banned, is_gbanned, get_auth_users


def owner_only(func):
    """Restrict command to bot owner only."""
    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        if message.from_user and message.from_user.id == Config.OWNER_ID:
            return await func(client, message, *args, **kwargs)
        # Silently ignore — owner commands are hidden
    return wrapper


def admin_or_auth(func):
    """Allow group admins and authorized users only."""
    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        if not message.from_user:
            return
        user_id = message.from_user.id
        chat_id = message.chat.id

        # Owner always allowed
        if user_id == Config.OWNER_ID:
            return await func(client, message, *args, **kwargs)

        # Check global ban
        if await is_gbanned(user_id):
            return await message.reply("❌ You are globally banned from using this bot.")

        # Check local ban
        if await is_banned(user_id):
            return await message.reply("❌ You are banned from using this bot.")

        # Check admin
        try:
            member = await client.get_chat_member(chat_id, user_id)
            if member.status in ("administrator", "creator"):
                return await func(client, message, *args, **kwargs)
        except Exception:
            pass

        # Check auth list
        auth_users = await get_auth_users(chat_id)
        if user_id in auth_users:
            return await func(client, message, *args, **kwargs)

        await message.reply("⚠️ Only group admins or authorized users can use this command.")

    return wrapper


def error_handler(func):
    """Catch exceptions, send to LOG_GROUP, show friendly message to user."""
    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        try:
            return await func(client, message, *args, **kwargs)
        except Exception as e:
            await send_error_log(f"Error in {func.__name__}: {e}", exc=e)
            try:
                await message.reply("Something went wrong 🌸")
            except Exception:
                pass
    return wrapper
