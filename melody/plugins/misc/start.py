"""
🚀 /start — Ultra-premium Melody welcome
   • HTML blockquote + bold/italic formatting everywhere
   • Animated sticker on start (if WELCOME_STICKER set)
   • User buttons vs Owner panel buttons
   • Color-coded emoji buttons (🔵 normal | 🔴 danger | 🟢 music)
   • Rich "thank you" welcome card when bot is added to a group
"""
import html
import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from melody import bot
from melody.config import Config
from melody.logging import log_activity
from utils.decorators import error_handler
from utils.database import is_banned, is_gbanned, get_chat_owner
from strings.themes import BLUE, RED, GREEN, btn, fancy

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets")
BG_START = os.path.join(ASSETS, "bg_start.png")
# Dedicated picture for the "bot added to a group" welcome card — set via
# /setwelcomepic (see melody/plugins/owner/set_welcome_pic.py). Falls back
# to BG_START, then to a text-only card, if not set.
BG_WELCOME = os.path.join(ASSETS, "bg_welcome.png")

# ─── Formatted text blocks ────────────────────────────────────────────────────

WELCOME_DM = (
    "<blockquote>"
    f"🎶 <b>{fancy('MELODY MUSIC BOT')}</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━"
    "</blockquote>\n\n"
    "🎵 <b>Premium Telegram Music Bot</b>\n"
    "<i>Stream HD music directly in your group voice chats!</i>\n\n"
    "<blockquote>"
    "✨ <b>Features:</b>\n"
    "  ▸ 🔥 YouTube HD streaming\n"
    "  ▸ 🎛 Inline music controls\n"
    "  ▸ 📋 Smart queue manager\n"
    "  ▸ 🔁 Loop &amp; AutoPlay\n"
    "  ▸ 🎤 Genius lyrics\n"
    "  ▸ 🖼 Beautiful play cards"
    "</blockquote>\n\n"
    f"♛ <b>Powered by</b> <code>{html.escape(Config.OWNER_NAME)}</code>\n"
    "💛 <i>Made with love for music lovers</i>"
)

# Richer welcome text shown when the bot is added to a group.
# {chat} and {user} are substituted at send time.
WELCOME_GROUP = (
    "<blockquote>"
    "🎶 <b>𝑴𝒆𝒍𝒐𝒅𝒚 𝑴𝒖𝒔𝒊𝒄 𝑩𝒐𝒕</b> has joined <b>{chat}</b>! 🎉"
    "</blockquote>\n\n"
    "🙏 Thanks for adding me, <b>{user}</b>!\n\n"
    "<blockquote expandable>"
    "🎵 <b>Quick Start</b>\n"
    "┌ <code>/play &lt;song&gt;</code> — Stream a song\n"
    "├ <code>/vplay &lt;song&gt;</code> — Stream video\n"
    "├ <code>/queue</code> — View the queue\n"
    "├ <code>/skip</code>  —  Skip current song\n"
    "├ <code>/stop</code>  —  Stop &amp; leave VC\n"
    "└ <code>/help</code>  —  Full command list\n\n"
    "🔥 <b>Power Features</b>\n"
    "┌ Loop mode · AutoPlay · Lyrics\n"
    "├ Beautiful now-playing cards\n"
    "└ Inline controls (pause / skip / stop)"
    "</blockquote>\n\n"
    f"♛ <i>Powered by {html.escape(Config.OWNER_NAME)}</i>"
)


# ─── Button layouts (color-coded with emoji) ──────────────────────────────────

def user_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(btn("▶ Play Music", RED), switch_inline_query_current_chat=""),
            InlineKeyboardButton(btn("📖 Help", BLUE), callback_data="help_main"),
        ],
        [
            InlineKeyboardButton(
                btn("➕ Add Me to Group", BLUE),
                url=f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}?startgroup=true",
            ),
        ],
        [
            InlineKeyboardButton(btn("📢 Support", BLUE), url="https://t.me/+0000000000000000"),
            InlineKeyboardButton(btn("ℹ About", BLUE), callback_data="about_cb"),
        ],
    ])


def owner_buttons() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(btn("▶ Play Music", RED), switch_inline_query_current_chat=""),
            InlineKeyboardButton(btn("📖 Help", BLUE), callback_data="help_main"),
        ],
        [
            InlineKeyboardButton(
                btn("➕ Add Me to Group", BLUE),
                url=f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}?startgroup=true",
            ),
        ],
        [
            InlineKeyboardButton(btn("👑 Owner Panel", RED), callback_data="owner_panel"),
        ],
    ])


def new_group_buttons(owner_id: int = None, owner_name: str = None) -> InlineKeyboardMarkup:
    """
    Rich button row shown when the bot is first added to a group.

    REQUEST: "jo user bot ko group add karega uska naam my cute owner me
    show kr" — whoever added the bot to this specific group gets credited
    as its "Cute Owner" with their own dedicated button (tapping it opens
    their profile). Falls back to no extra row if we somehow don't have an
    adder (e.g. legacy chat with no stored owner).
    """
    rows = [
        [
            InlineKeyboardButton(btn("🎵 Play Music", GREEN), switch_inline_query_current_chat=""),
            InlineKeyboardButton(btn("📖 Help", BLUE), callback_data="help_main"),
        ],
    ]
    if owner_id and owner_name:
        # FIX: tapping this button used to only pop up a text alert
        # (callback_data="cute_owner") instead of actually opening the
        # owner's profile. `tg://user?id=<id>` IS a Bot-API-supported URL
        # scheme for inline buttons (Telegram resolves it to that user's
        # profile inside the client) — it opens their chat/profile directly,
        # which is what was actually requested.
        rows.append([
            InlineKeyboardButton(
                btn(f"👑 My Cute Owner: {owner_name}", GREEN),
                url=f"tg://user?id={owner_id}",
            ),
        ])
    rows.extend([
        [
            InlineKeyboardButton(
                btn("➕ Add to Another Group", BLUE),
                url=f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}?startgroup=true",
            ),
        ],
        [
            InlineKeyboardButton(btn("📢 Support Channel", BLUE), url="https://t.me/+0000000000000000"),
            InlineKeyboardButton(btn("ℹ About", BLUE), callback_data="about_cb"),
        ],
    ])
    return InlineKeyboardMarkup(rows)


# ─── /start in DM ─────────────────────────────────────────────────────────────

@bot.on_message(filters.command("start") & filters.private)
@error_handler
async def start_dm(client: Client, message: Message):
    if message.from_user:
        if await is_gbanned(message.from_user.id):
            return
        if await is_banned(message.from_user.id):
            return await message.reply(
                "<b>❌ You are banned from using this bot.</b>",
                parse_mode=enums.ParseMode.HTML,
            )

    is_owner = bool(message.from_user and message.from_user.id == Config.OWNER_ID)

    # ── Log who started the bot (owner launches vs. a regular user's first DM) ──
    user = message.from_user
    if user:
        role = "👑 Owner" if is_owner else "🙋 User"
        uname = f"@{user.username}" if user.username else "—"
        asyncio.create_task(log_activity(
            f"🚀 <b>Bot Started</b>\n"
            f"• {role}: <code>{html.escape(user.first_name)}</code> ({uname})\n"
            f"• User ID: <code>{user.id}</code>"
        ))

    # ── Animated sticker (if configured) ──
    if Config.WELCOME_STICKER:
        try:
            await message.reply_sticker(Config.WELCOME_STICKER)
        except Exception:
            pass

    markup = owner_buttons() if is_owner else user_buttons()

    if os.path.exists(BG_START):
        await message.reply_photo(
            BG_START,
            caption=WELCOME_DM,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=markup,
        )
    else:
        await message.reply(
            WELCOME_DM,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=markup,
        )


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
            InlineKeyboardButton(btn("▶ Play Music", RED), switch_inline_query_current_chat=""),
            InlineKeyboardButton(btn("📖 Help", BLUE), callback_data="help_main"),
        ],
        [
            InlineKeyboardButton(
                btn("➕ Add to Another Group", BLUE),
                url=f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}?startgroup=true",
            ),
        ],
    ])
    await message.reply(
        f"<blockquote>🎶 <b>{fancy('MELODY')}</b> is ready to rock this group! 🎵</blockquote>\n\n"
        "Use <code>/play &lt;song name or YouTube link&gt;</code> to start the music.\n"
        "Use <code>/help</code> to see all available commands.\n\n"
        f"♛ <i>Powered by {html.escape(Config.OWNER_NAME)}</i>",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=buttons,
    )


# ─── Bot added to a new group — rich "thank you" welcome card ─────────────────

@bot.on_message(filters.new_chat_members)
@error_handler
async def new_group_handler(client: Client, message: Message):
    bot_user = await client.get_me()
    for member in message.new_chat_members:
        if member.id != bot_user.id:
            continue

        chat  = message.chat
        adder = message.from_user

        from utils.database import add_chat
        await add_chat(
            chat.id,
            chat.title or "",
            owner_id=adder.id if adder else None,
            owner_name=(adder.first_name if adder else None),
        )

        member_count = None
        try:
            member_count = await client.get_chat_members_count(chat.id)
        except Exception:
            pass

        adder_uname = f"@{adder.username}" if (adder and adder.username) else "—"
        asyncio.create_task(log_activity(
            f"➕ <b>New Group Added</b>\n"
            f"• Chat: <code>{html.escape(chat.title or '')}</code>\n"
            f"• Chat ID: <code>{chat.id}</code>\n"
            f"• Type: <code>{chat.type.value if chat.type else 'unknown'}</code>\n"
            + (f"• Members: <code>{member_count}</code>\n" if member_count is not None else "")
            + f"• Added by: <code>{html.escape(adder.first_name) if adder else 'unknown'}</code> "
              f"({adder_uname}, <code>{adder.id if adder else 'unknown'}</code>)"
        ))

        adder_name = html.escape(adder.first_name if adder else "there")
        chat_name  = html.escape(chat.title or "this group")
        members_line = (
            f"\n👥 <b>Members:</b> <code>{member_count}</code>" if member_count else ""
        )

        # Build the caption with member count appended nicely
        caption = WELCOME_GROUP.format(chat=chat_name, user=adder_name) + members_line
        buttons = new_group_buttons(
            owner_id=adder.id if adder else None,
            owner_name=(adder.first_name if adder else None),
        )

        # Prefer the dedicated group-welcome pic; fall back to the start
        # pic, then to a text-only card.
        welcome_pic = BG_WELCOME if os.path.exists(BG_WELCOME) else (BG_START if os.path.exists(BG_START) else None)

        if welcome_pic:
            await message.reply_photo(
                welcome_pic,
                caption=caption,
                parse_mode=enums.ParseMode.HTML,
                reply_markup=buttons,
            )
        else:
            # No custom pic set yet — send an attractive text card with a
            # blockquote header so it still looks polished in the chat.
            await message.reply(
                "<blockquote>"
                "🎶 <b>𝑴𝒆𝒍𝒐𝒅𝒚 𝑴𝒖𝒔𝒊𝒄 𝑩𝒐𝒕</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━"
                "</blockquote>\n\n"
                + caption,
                parse_mode=enums.ParseMode.HTML,
                reply_markup=buttons,
            )
        break


# ─── Cute Owner callback ────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^cute_owner$"))
@error_handler
async def cb_cute_owner(client: Client, cb: CallbackQuery):
    owner = await get_chat_owner(cb.message.chat.id)
    if owner and owner.get("owner_name"):
        text = f"👑 {owner['owner_name']} added Melody to this group. Say thanks! 🎶"
    else:
        text = "👑 This group's Cute Owner is a mystery for now! 🎶"
    await cb.answer(text, show_alert=True)


# ─── About callback ───────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^about_cb$"))
@error_handler
async def cb_about(client: Client, cb: CallbackQuery):
    await cb.message.edit_text(
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
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(btn("◀ Back", RED), callback_data="start_back")],
        ]),
    )
    await cb.answer()


# ─── Back to Home ─────────────────────────────────────────────────────────────

@bot.on_callback_query(filters.regex(r"^owner_back_home$"))
@error_handler
async def cb_owner_back_home(client: Client, cb: CallbackQuery):
    if cb.from_user.id != Config.OWNER_ID:
        return await cb.answer("❌ Owner only!", show_alert=True)

    await cb.message.edit_text(
        WELCOME_DM,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=owner_buttons(),
    )
    await cb.answer()


@bot.on_callback_query(filters.regex(r"^start_back$"))
@error_handler
async def cb_start_back(client: Client, cb: CallbackQuery):
    is_owner = cb.from_user.id == Config.OWNER_ID
    await cb.message.edit_text(
        WELCOME_DM,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=owner_buttons() if is_owner else user_buttons(),
    )
    await cb.answer()
