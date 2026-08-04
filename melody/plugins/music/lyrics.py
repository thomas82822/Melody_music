"""
🎵 /lyrics command — fetches from Genius API

FIX: genius.search_song() is a SYNCHRONOUS/blocking HTTP call. Calling it
     directly inside an async handler blocks the entire asyncio event loop
     (all other Telegram updates pause until the HTTP request completes).
     Wrapped in asyncio.get_running_loop().run_in_executor() to run it
     in a thread pool so the bot stays responsive.
"""
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.config import Config
from melody.core.queue import get_current
from utils.decorators import error_handler


@bot.on_message(filters.command("lyrics") & filters.group)
@error_handler
async def lyrics_cmd(client: Client, message: Message):
    query = " ".join(message.command[1:])
    if not query:
        current = get_current(message.chat.id)
        if not current:
            await message.reply("❌ Nothing is playing. Use `/lyrics <song name>`")
            return
        query = current.title

    if not Config.GENIUS_API_TOKEN:
        await message.reply("⚠️ Genius API token not configured.")
        return

    msg = await message.reply(f"🔍 Fetching lyrics for: `{query}`...")

    try:
        import lyricsgenius
        genius = lyricsgenius.Genius(
            Config.GENIUS_API_TOKEN,
            verbose=False,
            remove_section_headers=True,
        )
        # FIX: run blocking HTTP call in a thread pool — never block event loop
        loop = asyncio.get_running_loop()
        song = await loop.run_in_executor(None, lambda: genius.search_song(query))

        if not song:
            await msg.edit("❌ Lyrics not found 🌸")
            return

        lyrics = song.lyrics[:4000]
        text = f"**🎵 {song.title}** — _{song.artist}_\n\n{lyrics}"
        await msg.edit(text[:4096])

    except Exception:
        await msg.edit("❌ Could not fetch lyrics 🌸")
