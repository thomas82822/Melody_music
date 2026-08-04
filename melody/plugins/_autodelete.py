"""
🧹 Global command auto-delete + 📋 A2Z activity logger
────────────────────────────────────────────────────────────────────────────
Requirement #2: the user's own command message must vanish instantly
(0.0 sec) after Telegram delivers it to the bot.

Requirement #3: EVERY command used anywhere (not just errors) must be
logged to LOG_GROUP_ID — a full "A2Z" activity trail.

Implementation notes
─────────────────────
• Registered in `group=-1` (Pyrogram dispatches groups in ascending order),
  so this runs BEFORE the real command handler in group 0 gets a chance.
• The delete is fired with `asyncio.create_task()` and NOT awaited before
  we hand off control — the coroutine that actually calls
  `message.delete()` starts executing on the very next event-loop tick,
  which is as close to "0.0 sec" as an async Telegram bot can get. We do
  not block command processing on the delete's network round-trip.
• `raise ContinuePropagation` lets Pyrogram continue on to the next group
  so the actual command handler (in group 0) still runs normally.
• Deletion requires the bot to have "Delete Messages" admin rights in the
  group. If it doesn't, the delete silently no-ops — we never surface a
  permission error to the chat, only to LOG_GROUP_ID (debug-level, so it
  doesn't spam the log group on every single message).
"""
import html
from pyrogram import Client, filters, ContinuePropagation
from pyrogram.types import Message
from melody import bot
from melody.logging import log_activity, LOGGER

ALL_COMMANDS = [
    "start", "help", "about", "ping", "stats",
    "play", "vplay", "pause", "resume", "skip", "s", "stop",
    "queue", "q", "np", "volume", "mute", "unmute",
    "loop", "loopall", "noloop", "shuffle", "clearqueue", "remove",
    "seek", "rewind", "speed", "search", "lyrics", "autoplay",
    "auth", "unauth", "authlist", "ban", "unban", "gban", "ungban",
    "broadcast", "chatlist", "maintenance",
    "reboot", "restart", "reload", "update", "logs", "panel",
    "activevc", "setpic", "delpic",
    "eval", "py", "shell", "sh", "bash", "exec",
]


async def _safe_delete(message: Message):
    try:
        await message.delete()
    except Exception as exc:
        LOGGER.debug("auto-delete: could not remove message %s: %s", message.id, exc)


@bot.on_message(filters.command(ALL_COMMANDS) & filters.group, group=-1)
async def _delete_and_log_command(client: Client, message: Message):
    # Fire-and-forget deletion — do NOT await before continuing dispatch.
    import asyncio
    asyncio.create_task(_safe_delete(message))

    # A2Z logging — every command, everywhere, fire-and-forget too so the
    # log-group round trip never adds latency to the real command handler.
    user = message.from_user
    chat = message.chat
    user_label = (
        f"{html.escape(user.first_name or 'Unknown')} (<code>{user.id}</code>)"
        if user else "Unknown"
    )
    chat_label = f"{html.escape(chat.title or 'Private')} (<code>{chat.id}</code>)"
    cmd_text = html.escape(message.text or "")
    asyncio.create_task(log_activity(
        f"🧾 <b>Command</b>\n"
        f"• Cmd: <code>{cmd_text}</code>\n"
        f"• User: {user_label}\n"
        f"• Chat: {chat_label}"
    ))

    raise ContinuePropagation
