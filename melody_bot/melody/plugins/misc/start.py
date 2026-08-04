"""
🚀 /start — Ultra-attractive Modi-Meloni welcome
"""
import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from melody import bot
from melody.config import Config
from utils.decorators import error_handler
from utils.database import is_banned, is_gbanned

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets")
BG_START = os.path.join(ASSETS, "bg_start.png")


@bot.on_message(filters.command("start"))
@error_handler
async def start_cmd(client: Client, message: Message):
    if message.from_user:
        if await is_gbanned(message.from_user.id):
            return
        if await is_banned(message.from_user.id):
            return await message.reply("❌ You are banned from using this bot.")

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️ Play Music", switch_inline_query_current_chat=""),
            InlineKeyboardButton("📋 Help", callback_data="help_main"),
        ],
        [
            InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}?startgroup=true"),
        ],
    ])

    caption = (
        "🎶 **MELODY** — _Har dil ki awaaz_\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎵 **Premium Music Bot** for Telegram\n"
        "🔥 YouTube streaming • HD quality\n"
        "🎛 Colored controls • Lyrics • AutoPlay\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"♛ **Powered by** `{Config.OWNER_NAME}`\n"
        "💛 _Made with love for music lovers_"
    )

    if os.path.exists(BG_START):
        await message.reply_photo(BG_START, caption=caption, reply_markup=buttons)
    else:
        await message.reply(caption, reply_markup=buttons)


@bot.on_message(filters.new_chat_members)
@error_handler
async def new_group_handler(client: Client, message: Message):
    bot_user = await client.get_me()
    for member in message.new_chat_members:
        if member.id == bot_user.id:
            chat = message.chat
            adder = message.from_user

            # Save chat to DB
            from utils.database import add_chat
            await add_chat(chat.id, chat.title or "")

            # Log to LOG_GROUP (private — no real names exposed publicly)
            from melody.logging import send_error_log
            try:
                await bot.send_message(
                    Config.LOG_GROUP_ID,
                    f"**➕ New Group Added**\n"
                    f"• Chat: `{chat.title}`\n"
                    f"• Chat ID: `{chat.id}`\n"
                    f"• Added by: `{adder.id if adder else 'unknown'}`",
                )
            except Exception:
                pass

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("▶️ Play Now", switch_inline_query_current_chat=""),
                    InlineKeyboardButton("📋 Help", callback_data="help_main"),
                ],
            ])

            caption = (
                f"🎶 **MELODY** is here!\n\n"
                f"Hey **{adder.first_name if adder else 'there'}**! Thanks for adding me to **{chat.title}**\n\n"
                f"🎵 Use `/play <song>` to start music\n"
                f"📋 Use `/help` to see all commands\n\n"
                f"♛ _Powered by {Config.OWNER_NAME}_"
            )

            if os.path.exists(BG_START):
                await message.reply_photo(BG_START, caption=caption, reply_markup=buttons)
            else:
                await message.reply(caption, reply_markup=buttons)
            break
