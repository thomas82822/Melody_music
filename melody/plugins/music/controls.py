"""
🎛 Playback controls — pause, resume, skip, stop + inline button handlers
BUG FIX: @error_handler moved OUTSIDE @admin_or_auth
"""
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from melody import bot
from melody.core.call import pause_stream, resume_stream, skip_stream, stop_stream
from melody.core.queue import format_queue, get_current
from utils.decorators import admin_or_auth, error_handler
from utils.formatters import format_duration


# ─── Message commands ─────────────────────────────────────────────────────────

@bot.on_message(filters.command("pause") & filters.group)
@error_handler
@admin_or_auth
async def pause_cmd(client: Client, message: Message):
    await pause_stream(message.chat.id)
    await message.reply("⏸ **Paused.**")


@bot.on_message(filters.command("resume") & filters.group)
@error_handler
@admin_or_auth
async def resume_cmd(client: Client, message: Message):
    await resume_stream(message.chat.id)
    await message.reply("▶️ **Resumed.**")


@bot.on_message(filters.command(["skip", "s"]) & filters.group)
@error_handler
@admin_or_auth
async def skip_cmd(client: Client, message: Message):
    await skip_stream(message.chat.id)
    await message.reply("⏭ **Skipped.**")


@bot.on_message(filters.command("stop") & filters.group)
@error_handler
@admin_or_auth
async def stop_cmd(client: Client, message: Message):
    await stop_stream(message.chat.id)
    await message.reply("⏹ **Music stopped and queue cleared.**")


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
    await cb.message.reply(text)


@bot.on_callback_query(filters.regex("^lyrics$"))
@error_handler
async def lyrics_callback(client: Client, cb: CallbackQuery):
    await cb.answer("🎵 Fetching lyrics...")
    track = get_current(cb.message.chat.id)
    if not track:
        await cb.message.reply("❌ Nothing is playing right now.")
        return

    try:
        import lyricsgenius
        from melody.config import Config
        if not Config.GENIUS_API_TOKEN:
            await cb.message.reply("⚠️ Genius API token not configured.")
            return

        genius = lyricsgenius.Genius(Config.GENIUS_API_TOKEN, verbose=False, remove_section_headers=True)
        import asyncio
        loop = asyncio.get_running_loop()
        song = await loop.run_in_executor(None, lambda: genius.search_song(track.title, track.uploader))
        if song and song.lyrics:
            lyrics_text = song.lyrics[:3500]
            await cb.message.reply(f"🎵 **{track.title}**\n\n{lyrics_text}")
        else:
            await cb.message.reply("❌ Lyrics not found.")
    except Exception as exc:
        await cb.message.reply("❌ Could not fetch lyrics.")
