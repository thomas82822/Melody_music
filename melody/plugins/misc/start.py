"""
🚀 /start — Ultra-premium Melody Music Bot welcome
   DM:    User buttons + Owner panel (if owner)
   Group: Attractive join welcome
"""
import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from melody import bot
from melody.config import Config
from utils.decorators import error_handler
from utils.database import is_banned, is_gbanned

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets")
BG_START = os.path.join(ASSETS, "bg_start.png")

# ─── Button layouts ───────────────────────────────────────────────────────────

def user_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵  Play Music", switch_inline_query_current_chat=""),
            InlineKeyboardButton("📖  Help", callback_data="help_main"),
        ],
        [
            InlineKeyboardButton(
                "➕  Add Me to Your Group",
                url=f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}?startgroup=true",
            ),
        ],
        [
            InlineKeyboardButton("📢  Support", url="https://t.me/+0000000000000000"),
            InlineKeyboardButton("ℹ️  About", callback_data="about_cb"),
        ],
    ])


def owner_buttons() -> InlineKeyboardMarkup:
    """Shown ONLY to the owner in DM."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵  Play Music", switch_inline_query_current_chat=""),
            InlineKeyboardButton("📖  Help", callback_data="help_main"),
        ],
        [
            InlineKeyboardButton(
                "➕  Add Me to Your Group",
                url=f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}?startgroup=true",
            ),
        ],
        [
            InlineKeyboardButton("👑  Owner Panel", callback_data="owner_panel"),
        ],
    ])


def owner_panel_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🖼️  Set Start Pic", callback_data="owner_setpic_info"),
            InlineKeyboardButton("📡  Active VCs", callback_data="owner_activevc"),
        ],
        [
            InlineKeyboardButton("📢  Broadcast", callback_data="owner_broadcast_info"),
            InlineKeyboardButton("📊  Bot Stats", callback_data="owner_stats"),
        ],
        [
            InlineKeyboardButton("📋  Chat List", callback_data="owner_chatlist"),
            InlineKeyboardButton("🔧  Maintenance", callback_data="owner_maintenance"),
        ],
        [
            InlineKeyboardButton("🔄  Reload Plugins", callback_data="owner_reload"),
            InlineKeyboardButton("🔁  Restart Bot", callback_data="owner_restart"),
        ],
        [
            InlineKeyboardButton("◀️  Back", callback_data="owner_back_home"),
        ],
    ])


# ─── /start in DM ─────────────────────────────────────────────────────────────

@bot.on_message(filters.command("start") & filters.private)
@error_handler
async def start_dm(client: Client, message: Message):
    if message.from_user:
        if await is_gbanned(message.from_user.id):
            return
        if await is_banned(message.from_user.id):
            return await message.reply("❌ You are banned from using this bot.")

    is_owner = (
        message.from_user
        and message.from_user.id == Config.OWNER_ID
    )

    caption = (
        "🎶 **MELODY MUSIC BOT**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎵 **Premium Telegram Music Bot**\n"
        "Stream high-quality music directly in your group voice chats!\n\n"
        "✨ **Features:**\n"
        "  ▸ 🔥 YouTube HD streaming\n"
        "  ▸ 🎛 Inline music controls\n"
        "  ▸ 📋 Smart queue manager\n"
        "  ▸ 🔁 Loop & AutoPlay\n"
        "  ▸ 🎤 Genius lyrics\n"
        "  ▸ 🖼 Beautiful play cards\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"♛ **Powered by** `{Config.OWNER_NAME}`\n"
        "💛 _Made with love for music lovers_"
    )

    markup = owner_buttons() if is_owner else user_buttons()

    if os.path.exists(BG_START):
        await message.reply_photo(BG_START, caption=caption, reply_markup=markup)
    else:
        await message.reply(caption, reply_markup=markup)


# ─── /start in Groups ─────────────────────────────────────────────────────────

@bot.on_message(filters.command("start") & filters.group)
@error_handler
async def start_group(client: Client, message: Message):
    if message.from_user:
        if await is_gbanned(message.from_user.id):
            return
        if await is_banned(message.from_user.id):
            return

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("▶️  Play Music", switch_inline_query_current_chat=""),
            InlineKeyboardButton("📖  Help", callback_data="help_main"),
        ],
        [
            InlineKeyboardButton(
                "➕  Add to Another Group",
                url=f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}?startgroup=true",
            ),
        ],
    ])

    await message.reply(
        "🎶 **MELODY** is ready to rock this group!\n\n"
        "Use `/play <song name or YouTube link>` to start the music 🎵\n"
        "Use `/help` to see all available commands.\n\n"
        f"♛ _Powered by {Config.OWNER_NAME}_",
        reply_markup=buttons,
    )


# ─── Bot added to a new group ─────────────────────────────────────────────────

@bot.on_message(filters.new_chat_members)
@error_handler
async def new_group_handler(client: Client, message: Message):
    bot_user = await client.get_me()
    for member in message.new_chat_members:
        if member.id == bot_user.id:
            chat = message.chat
            adder = message.from_user

            # Save chat
            from utils.database import add_chat
            await add_chat(chat.id, chat.title or "")

            # Log to private group
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
                    InlineKeyboardButton("▶️  Play Now", switch_inline_query_current_chat=""),
                    InlineKeyboardButton("📖  Help", callback_data="help_main"),
                ],
                [
                    InlineKeyboardButton(
                        "➕  Add to Another Group",
                        url=f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}?startgroup=true",
                    ),
                ],
            ])

            adder_name = adder.first_name if adder else "there"
            caption = (
                f"🎶 **MELODY** has joined **{chat.title}**! 🎉\n\n"
                f"Hey **{adder_name}**, thanks for adding me! 🙏\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🎵 `/play <song>` — Start the music\n"
                "📋 `/queue` — View the queue\n"
                "⏭ `/skip` — Skip current song\n"
                "📖 `/help` — See all commands\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"♛ _Powered by {Config.OWNER_NAME}_"
            )

            if os.path.exists(BG_START):
                await message.reply_photo(BG_START, caption=caption, reply_markup=buttons)
            else:
                await message.reply(caption, reply_markup=buttons)
            break


# ─── Back to Home callback ────────────────────────────────────────────────────
# (owner_panel callback is handled in owner/panel.py)

@bot.on_callback_query(filters.regex(r"^owner_back_home$"))
@error_handler
async def cb_owner_back_home(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    caption = (
        "🎶 **MELODY MUSIC BOT**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎵 **Premium Telegram Music Bot**\n"
        "Stream high-quality music directly in your group voice chats!\n\n"
        "✨ **Features:**\n"
        "  ▸ 🔥 YouTube HD streaming\n"
        "  ▸ 🎛 Inline music controls\n"
        "  ▸ 📋 Smart queue manager\n"
        "  ▸ 🔁 Loop & AutoPlay\n"
        "  ▸ 🎤 Genius lyrics\n"
        "  ▸ 🖼 Beautiful play cards\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"♛ **Powered by** `{Config.OWNER_NAME}`\n"
        "💛 _Made with love for music lovers_"
    )
    await cb.message.edit_text(caption, reply_markup=owner_buttons())
    await cb.answer()


# ─── About callback ───────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^about_cb$"))
@error_handler
async def cb_about(client: Client, cb: CallbackQuery):
    await cb.message.edit_text(
        "🎶 **About Melody**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Melody** is a premium Telegram music bot that streams\nhigh-quality audio from YouTube.\n\n"
        "🔥 **Features:**\n"
        "  ▸ HD YouTube streaming\n"
        "  ▸ Smart queue management\n"
        "  ▸ AutoPlay with related songs\n"
        "  ▸ Genius lyrics integration\n"
        "  ▸ Beautiful now-playing cards\n"
        "  ▸ Group admin controls\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Made with 💛 by an anonymous developer 🌑\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️  Back", callback_data="start_back")],
        ]),
    )
    await cb.answer()


@bot.on_callback_query(filters.regex(r"^start_back$"))
@error_handler
async def cb_start_back(client: Client, cb: CallbackQuery):
    is_owner = cb.from_user.id == Config.OWNER_ID
    caption = (
        "🎶 **MELODY MUSIC BOT**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎵 **Premium Telegram Music Bot**\n"
        "Stream high-quality music directly in your group voice chats!\n\n"
        "✨ **Features:**\n"
        "  ▸ 🔥 YouTube HD streaming\n"
        "  ▸ 🎛 Inline music controls\n"
        "  ▸ 📋 Smart queue manager\n"
        "  ▸ 🔁 Loop & AutoPlay\n"
        "  ▸ 🎤 Genius lyrics\n"
        "  ▸ 🖼 Beautiful play cards\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"♛ **Powered by** `{Config.OWNER_NAME}`\n"
        "💛 _Made with love for music lovers_"
    )
    await cb.message.edit_text(
        caption,
        reply_markup=owner_buttons() if is_owner else user_buttons(),
    )
    await cb.answer()
