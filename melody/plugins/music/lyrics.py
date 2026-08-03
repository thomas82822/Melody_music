"""
🎵 /lyrics command — fetches from Genius API
"""
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

    msg = await message.reply(f"🔍 Fetching lyrics for: `{query}`...")

    try:
        import lyricsgenius
        genius = lyricsgenius.Genius(Config.GENIUS_API_TOKEN, verbose=False, remove_section_headers=True)
        song = genius.search_song(query)
        if not song:
            await msg.edit("❌ Lyrics not found 🌸")
            return

        lyrics = song.lyrics[:4000]  # Telegram message limit
        text = f"**🎵 {song.title}** — _{song.artist}_\n\n{lyrics}"
        await msg.edit(text[:4096])

    except Exception:
        await msg.edit("❌ Could not fetch lyrics 🌸")
