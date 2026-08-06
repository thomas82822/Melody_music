"""
🎛 Playback controls — pause, resume, skip, stop + inline button handlers
BUG FIX: @error_handler moved OUTSIDE @admin_or_auth
"""
import html
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message, CallbackQuery
from melody import bot
from melody.core.call import pause_stream, resume_stream, skip_stream, stop_stream
from melody.core.queue import format_queue, get_current, is_autoplay_on, set_autoplay
from melody.core.autoplay import prefetch_next
from melody.logging import log_activity
from utils.decorators import admin_or_auth, channel_admin_or_auth, error_handler
from utils.formatters import format_duration, send_quote, premium_emoji, PREMIUM_EMOJI_IDS
from utils.thumbnails import get_bot_identity

_PAUSE = premium_emoji(PREMIUM_EMOJI_IDS["pause"], "⏸")
_RESUME = premium_emoji(PREMIUM_EMOJI_IDS["resume"], "▶️")
_SKIP = premium_emoji(PREMIUM_EMOJI_IDS["skip"], "⏭")
_STOP = premium_emoji(PREMIUM_EMOJI_IDS["stop"], "⏹")


def _who(message: Message) -> tuple[str, str]:
    """Return (actor_html, chat_html) for a rich activity-log line."""
    user = message.from_user
    actor = html.escape(user.first_name) if user else "Someone"
    chat_name = html.escape(message.chat.title or str(message.chat.id))
    return actor, chat_name


# ─── Message commands ─────────────────────────────────────────────────────────

@bot.on_message(filters.command("pause") & filters.group)
@error_handler
@admin_or_auth
async def pause_cmd(client: Client, message: Message):
    await pause_stream(message.chat.id)
    await send_quote(message, f"{_PAUSE} <b>Paused.</b>", client=client)
    actor, chat_name = _who(message)
    asyncio.create_task(log_activity(f"⏸ <b>Paused</b>\n• By: <code>{actor}</code>\n• Chat: <code>{chat_name}</code>"))


@bot.on_message(filters.command("resume") & filters.group)
@error_handler
@admin_or_auth
async def resume_cmd(client: Client, message: Message):
    await resume_stream(message.chat.id)
    await send_quote(message, f"{_RESUME} <b>Resumed.</b>", client=client)
    actor, chat_name = _who(message)
    asyncio.create_task(log_activity(f"▶️ <b>Resumed</b>\n• By: <code>{actor}</code>\n• Chat: <code>{chat_name}</code>"))


@bot.on_message(filters.command(["skip", "s"]) & filters.group)
@error_handler
@admin_or_auth
async def skip_cmd(client: Client, message: Message):
    await skip_stream(message.chat.id)
    await send_quote(message, f"{_SKIP} <b>Skipped.</b>", client=client)
    actor, chat_name = _who(message)
    asyncio.create_task(log_activity(f"⏭ <b>Skipped</b>\n• By: <code>{actor}</code>\n• Chat: <code>{chat_name}</code>"))


@bot.on_message(filters.command(["stop", "end"]) & filters.group)
@error_handler
@admin_or_auth
async def stop_cmd(client: Client, message: Message):
    await stop_stream(message.chat.id)
    await send_quote(message, f"{_STOP} <b>Music stopped and queue cleared.</b>", client=client)
    actor, chat_name = _who(message)
    asyncio.create_task(log_activity(f"⏹ <b>Stopped</b>\n• By: <code>{actor}</code>\n• Chat: <code>{chat_name}</code>"))


# ─── Channel controls — same actions, usable directly inside a channel ───────
# Channels can host a voice chat exactly like groups; the auth model differs
# (channel_admin_or_auth trusts channel-authored posts), so these get their
# own command set rather than broadening the group filters above.

@bot.on_message(filters.command("cpause") & filters.channel)
@error_handler
@channel_admin_or_auth
async def cpause_cmd(client: Client, message: Message):
    await pause_stream(message.chat.id)
    await send_quote(message, f"{_PAUSE} <b>Paused.</b>", client=client)
    actor, chat_name = _who(message)
    asyncio.create_task(log_activity(f"⏸ <b>Paused (channel)</b>\n• By: <code>{actor}</code>\n• Chat: <code>{chat_name}</code>"))


@bot.on_message(filters.command("cresume") & filters.channel)
@error_handler
@channel_admin_or_auth
async def cresume_cmd(client: Client, message: Message):
    await resume_stream(message.chat.id)
    await send_quote(message, f"{_RESUME} <b>Resumed.</b>", client=client)
    actor, chat_name = _who(message)
    asyncio.create_task(log_activity(f"▶️ <b>Resumed (channel)</b>\n• By: <code>{actor}</code>\n• Chat: <code>{chat_name}</code>"))


@bot.on_message(filters.command(["cskip", "cs"]) & filters.channel)
@error_handler
@channel_admin_or_auth
async def cskip_cmd(client: Client, message: Message):
    await skip_stream(message.chat.id)
    await send_quote(message, f"{_SKIP} <b>Skipped.</b>", client=client)
    actor, chat_name = _who(message)
    asyncio.create_task(log_activity(f"⏭ <b>Skipped (channel)</b>\n• By: <code>{actor}</code>\n• Chat: <code>{chat_name}</code>"))


@bot.on_message(filters.command(["cstop", "cend"]) & filters.channel)
@error_handler
@channel_admin_or_auth
async def cstop_cmd(client: Client, message: Message):
    await stop_stream(message.chat.id)
    await send_quote(message, f"{_STOP} <b>Music stopped and queue cleared.</b>", client=client)
    actor, chat_name = _who(message)
    asyncio.create_task(log_activity(f"⏹ <b>Stopped (channel)</b>\n• By: <code>{actor}</code>\n• Chat: <code>{chat_name}</code>"))


# ─── Inline button callbacks ──────────────────────────────────────────────────

@bot.on_callback_query(filters.regex("^pause$"))
@error_handler
async def pause_callback(client: Client, cb: CallbackQuery):
    await cb.answer("⏸ Paused")
    await pause_stream(cb.message.chat.id)


@bot.on_callback_query(filters.regex("^resume$"))
@error_handler
async def resume_callback(client: Client, cb: CallbackQuery):
    await cb.answer("▶️ Resumed")
    await resume_stream(cb.message.chat.id)


@bot.on_callback_query(filters.regex("^skip$"))
@error_handler
async def skip_callback(client: Client, cb: CallbackQuery):
    await cb.answer("⏭ Skipped")
    await skip_stream(cb.message.chat.id)


@bot.on_callback_query(filters.regex("^stop$"))
@error_handler
async def stop_callback(client: Client, cb: CallbackQuery):
    await cb.answer("⏹ Stopped")
    await stop_stream(cb.message.chat.id)
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


@bot.on_callback_query(filters.regex("^queue$"))
@error_handler
async def queue_callback(client: Client, cb: CallbackQuery):
    await cb.answer()
    text = format_queue(cb.message.chat.id)
    await send_quote(cb.message, text, client=client)


@bot.on_callback_query(filters.regex("^autoplay_toggle$"))
@error_handler
async def autoplay_toggle_callback(client: Client, cb: CallbackQuery):
    """Inline AutoPlay toggle button on the play card.

    REQUEST: "Play card buttons me add kr autoplay" — lets group members
    flip AutoPlay on/off directly from the play card instead of typing
    /autoplay on|off, and re-renders the card's buttons in place so the
    label always reflects the current state.
    """
    chat_id = cb.message.chat.id
    new_state = not await is_autoplay_on(chat_id)
    await set_autoplay(chat_id, new_state)
    await cb.answer(f"🤖 AutoPlay {'ON 🟢' if new_state else 'OFF 🔴'}")

    if new_state and get_current(chat_id):
        asyncio.create_task(prefetch_next(chat_id))

    try:
        from melody.plugins.music.play import get_play_buttons
        bot_username, bot_name = await get_bot_identity(client)
        await cb.message.edit_reply_markup(
            reply_markup=get_play_buttons(cb.message.chat.title or "", new_state, bot_username, bot_name)
        )
    except Exception:
        pass  # button label refresh is best-effort; the toggle itself already applied

    actor = html.escape(cb.from_user.first_name) if cb.from_user else "Someone"
    chat_name = html.escape(cb.message.chat.title or str(cb.message.chat.id))
    asyncio.create_task(log_activity(
        f"🤖 <b>AutoPlay {'Enabled' if new_state else 'Disabled'} (via button)</b>\n"
        f"• By: <code>{actor}</code>\n• Chat: <code>{chat_name}</code>"
    ))


@bot.on_callback_query(filters.regex("^noop$"))
async def noop_callback(client: Client, cb: CallbackQuery):
    await cb.answer()


@bot.on_callback_query(filters.regex("^lyrics$"))
@error_handler
async def lyrics_callback(client: Client, cb: CallbackQuery):
    await cb.answer("🎵 Fetching lyrics...")
    track = get_current(cb.message.chat.id)
    if not track:
        await send_quote(cb.message, "❌ Nothing is playing right now.", client=client)
        return

    try:
        import lyricsgenius
        from melody.config import Config
        if not Config.GENIUS_API_TOKEN:
            await send_quote(cb.message, "⚠️ Genius API token not configured.", client=client)
            return

        genius = lyricsgenius.Genius(Config.GENIUS_API_TOKEN, verbose=False, remove_section_headers=True)
        import asyncio as _asyncio
        loop = _asyncio.get_running_loop()
        song = await loop.run_in_executor(None, lambda: genius.search_song(track.title, track.uploader))
        if song and song.lyrics:
            safe_title = html.escape(track.title)
            lyrics_text = html.escape(song.lyrics[:3500])
            await send_quote(
                cb.message,
                f"🎵 <b>{safe_title}</b>\n\n<blockquote expandable>{lyrics_text}</blockquote>",
                client=client,
            )
        else:
            await send_quote(cb.message, "❌ Lyrics not found.", client=client)
    except Exception:
        await send_quote(cb.message, "❌ Could not fetch lyrics.", client=client)
