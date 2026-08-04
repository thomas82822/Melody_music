"""
ℹ️ /about — anonymous about page
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from utils.decorators import error_handler


@bot.on_message(filters.command("about"))
@error_handler
async def about_cmd(client: Client, message: Message):
    await message.reply(
        "🎶 **About Melody**\n\n"
        "**Melody** is a premium Telegram music bot that streams from YouTube.\n\n"
        "🔥 **Features:**\n"
        "• HD YouTube streaming\n"
        "• Smart queue management\n"
        "• AutoPlay with related songs\n"
        "• Genius lyrics integration\n"
        "• Colored mini-app controls\n"
        "• Beautiful play cards\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Made with 💛 by an anonymous developer 🌑\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
