"""
ℹ️ /about — About page with HTML blockquote formatting
"""
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from melody import bot
from utils.decorators import error_handler

ABOUT_TEXT = (
    "<blockquote>🎶 <b>About Melody</b></blockquote>\n\n"
    "<b>Melody</b> is a premium Telegram music bot that streams\n"
    "high-quality audio from YouTube.\n\n"
    "<blockquote>"
    "🔥 <b>Features:</b>\n"
    "  ▸ HD YouTube streaming\n"
    "  ▸ Smart queue management\n"
    "  ▸ AutoPlay with related songs\n"
    "  ▸ Genius lyrics integration\n"
    "  ▸ Beautiful now-playing cards\n"
    "  ▸ Group admin controls"
    "</blockquote>\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "Made with 💀 by <b>Sasta Developer</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━"
)


@bot.on_message(filters.command("about"))
@error_handler
async def about_cmd(client: Client, message: Message):
    await message.reply(
        ABOUT_TEXT,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔴  ⊛ CLOSE ⊛", callback_data="about_close")],
        ]),
    )


from pyrogram.types import CallbackQuery

@bot.on_callback_query(filters.regex(r"^about_close$"))
@error_handler
async def about_close_cb(client: Client, cb: CallbackQuery):
    try:
        await cb.message.delete()
    except Exception:
        pass
    await cb.answer()
