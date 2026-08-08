"""
🔒 Decorators for permission checks
BUG FIX: error_handler now also handles errors from admin_or_auth (DB failures etc.)
"""
import asyncio
import functools
from pyrogram import Client
from pyrogram.errors import FloodWait
from pyrogram.types import Message, CallbackQuery
from melody.config import Config
from melody.logging import LOGGER, send_error_log
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

        # Check admin — Pyrogram 2.x uses str-enum so string compare works
        try:
            member = await client.get_chat_member(chat_id, user_id)
            # status values: "creator", "administrator", "member", "restricted", "left", "kicked"
            if str(member.status) in ("ChatMemberStatus.OWNER", "ChatMemberStatus.ADMINISTRATOR",
                                       "creator", "administrator"):
                return await func(client, message, *args, **kwargs)
        except Exception:
            pass

        # Check auth list
        auth_users = await get_auth_users(chat_id)
        if user_id in auth_users:
            return await func(client, message, *args, **kwargs)

        await message.reply("⚠️ Only group admins or authorized users can use this command.")

    return wrapper


def channel_admin_or_auth(func):
    """Permission gate for commands usable directly inside a channel
    (channel play/controls), where the invoking message may be a genuine
    channel post instead of a normal user message.

    Telegram only allows channel admins to author a post that appears as
    coming from the channel itself (message.from_user is None in that case,
    message.sender_chat is the channel) — so any such message is implicitly
    admin-authored and safe to allow. If the message DOES have a from_user
    (e.g. sent from a discussion group linked to the channel, or Telegram
    surfaces the real author), fall back to the same checks as
    admin_or_auth.
    """
    @functools.wraps(func)
    async def wrapper(client: Client, message: Message, *args, **kwargs):
        chat_id = message.chat.id

        if message.from_user is None:
            # Genuine channel post — only channel admins can author these.
            return await func(client, message, *args, **kwargs)

        user_id = message.from_user.id

        if user_id == Config.OWNER_ID:
            return await func(client, message, *args, **kwargs)

        if await is_gbanned(user_id):
            return await message.reply("❌ You are globally banned from using this bot.")

        if await is_banned(user_id):
            return await message.reply("❌ You are banned from using this bot.")

        try:
            member = await client.get_chat_member(chat_id, user_id)
            if str(member.status) in ("ChatMemberStatus.OWNER", "ChatMemberStatus.ADMINISTRATOR",
                                       "creator", "administrator"):
                return await func(client, message, *args, **kwargs)
        except Exception:
            pass

        auth_users = await get_auth_users(chat_id)
        if user_id in auth_users:
            return await func(client, message, *args, **kwargs)

        await message.reply("⚠️ Only channel admins or authorized users can use this command.")

    return wrapper


def error_handler(func):
    """
    Catch ALL exceptions (including from nested decorators like admin_or_auth).
    Send traceback to LOG_GROUP and show friendly message to user.
    Works for both Message handlers and CallbackQuery handlers.

    BUG FIX (⚠️ Melody Error Log spam / crash on FloodWait):
    A FloodWait raised by Telegram (420 FLOOD_WAIT_X) is normal rate-limit
    back-pressure, not a bug — it used to be treated exactly like any other
    exception here: logged to LOG_GROUP as an "error" AND immediately
    retried by sending yet another message ("Something went wrong 🌸") to
    the same flood-controlled chat/method, which just as easily hits the
    SAME flood wait again (or a longer one) and raises a second, uncaught
    FloodWait right out of this handler. Client.sleep_threshold (see
    melody/__init__.py) now makes Pyrogram auto-sleep-and-retry any
    FLOOD_WAIT_X up to 60s transparently, so this branch only ever fires
    for waits longer than that. In that rarer case: sleep out the wait
    once and retry the original command a single time instead of sending
    a second message into the same flood window; never re-log FloodWait
    as an "error" (it isn't one) and never let a retry's own FloodWait
    cascade into more exceptions.
    """
    @functools.wraps(func)
    async def wrapper(client, update, *args, **kwargs):
        try:
            return await func(client, update, *args, **kwargs)
        except FloodWait as e:
            LOGGER.warning("FloodWait %ss in %s — sleeping once and retrying.", e.value, func.__name__)
            try:
                await asyncio.sleep(e.value)
                return await func(client, update, *args, **kwargs)
            except Exception:
                # Retry itself failed (likely flooded again) — give up quietly.
                # No user-facing message and no error-log spam for flood control.
                pass
        except Exception as e:
            # Build structured context from the update so the log channel
            # shows which command, which chat, and which user triggered
            # the error — not just a bare function name and traceback.
            ctx = {"command": func.__name__}
            try:
                if isinstance(update, CallbackQuery):
                    if update.message and update.message.chat:
                        ctx["chat_id"] = update.message.chat.id
                        ctx["chat_title"] = update.message.chat.title
                    if update.from_user:
                        ctx["user_id"] = update.from_user.id
                        ctx["user_name"] = update.from_user.first_name or ""
                elif hasattr(update, "chat") and update.chat:
                    ctx["chat_id"] = update.chat.id
                    ctx["chat_title"] = update.chat.title
                if hasattr(update, "from_user") and update.from_user:
                    ctx["user_id"] = update.from_user.id
                    ctx["user_name"] = update.from_user.first_name or ""
            except Exception:
                pass
            await send_error_log(f"Error in {func.__name__}: {e}", exc=e, context=ctx)
            try:
                # update can be Message or CallbackQuery
                if isinstance(update, CallbackQuery):
                    await update.answer("Something went wrong 🌸", show_alert=True)
                else:
                    await update.reply("Something went wrong 🌸")
            except Exception:
                pass
    return wrapper
