"""
📋 /help — 3-column color-coded help menu (reference image style)
   • 🟢 Green  = music/play actions
   • 🔵 Blue   = normal/info actions
   • 🔴 Red    = danger/back/important
   • HTML blockquote formatting throughout
"""
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from melody import bot
from melody.config import Config
from utils.decorators import error_handler

# ─── Help page text (HTML) ────────────────────────────────────────────────────

HELP_PAGES = {
    "play": (
        "<blockquote>🟢 <b>Play Commands</b></blockquote>\n\n"
        "<code>/play [song/url]</code> — ▶️ Play from YouTube\n"
        "<code>/vplay [song/url]</code> — 🎬 Video stream\n"
        "<code>/search [query]</code> — 🔍 Search &amp; pick a song\n\n"
        "<i>Tip: Works with YouTube links or just the song name!</i>"
    ),
    "queue": (
        "<blockquote>🔵 <b>Queue Commands</b></blockquote>\n\n"
        "<code>/queue</code> <code>/q</code> — 📋 View the queue\n"
        "<code>/skip</code> <code>/s</code> — ⏭ Skip current song\n"
        "<code>/shuffle</code> — 🔀 Shuffle the queue\n"
        "<code>/clearqueue</code> — 🗑 Clear entire queue\n"
        "<code>/remove [pos]</code> — ❌ Remove from queue"
    ),
    "controls": (
        "<blockquote>🔴 <b>Control Commands</b></blockquote>\n\n"
        "<code>/pause</code> — ⏸ Pause playback\n"
        "<code>/resume</code> — ▶️ Resume playback\n"
        "<code>/stop</code> — ⏹ Stop &amp; clear queue\n"
        "<code>/seek [sec]</code> — ⏩ Seek forward\n"
        "<code>/rewind [sec]</code> — ⏪ Seek backward\n"
        "<code>/np</code> — 🎶 Now playing info"
    ),
    "loop": (
        "<blockquote>🔵 <b>Loop Commands</b></blockquote>\n\n"
        "<code>/loop</code> — 🔂 Loop current song\n"
        "<code>/loopall</code> — 🔁 Loop the entire queue\n"
        "<code>/noloop</code> — ➡️ Disable looping\n"
        "<code>/autoplay on/off</code> — 🤖 Toggle autoplay"
    ),
    "volume": (
        "<blockquote>🔵 <b>Volume &amp; Speed</b></blockquote>\n\n"
        "<code>/volume [1-200]</code> — 🔊 Set volume level\n"
        "<code>/mute</code> — 🔇 Mute audio\n"
        "<code>/unmute</code> — 🔈 Unmute audio\n"
        "<code>/speed [0.5-2.0]</code> — ⏱ Playback speed"
    ),
    "seek": (
        "<blockquote>🟢 <b>Seek &amp; Navigation</b></blockquote>\n\n"
        "<code>/seek [seconds]</code> — ⏩ Seek forward\n"
        "<code>/rewind [seconds]</code> — ⏪ Seek backward\n\n"
        "<i>Example: /seek 30 → skips 30 seconds forward</i>"
    ),
    "ping": (
        "<blockquote>🔵 <b>Info Commands</b></blockquote>\n\n"
        "<code>/ping</code> — 🏓 Bot response latency\n"
        "<code>/stats</code> — 📊 Bot statistics\n"
        "<code>/about</code> — 🎶 About Melody"
    ),
    "lyrics": (
        "<blockquote>🔵 <b>Lyrics</b></blockquote>\n\n"
        "<code>/lyrics [song name]</code> — 🎤 Get Genius lyrics\n\n"
        "<i>If no song name given, fetches lyrics for the currently playing song.</i>"
    ),
    "admin": (
        "<blockquote>🔴 <b>Admin Commands</b> <i>(Group Admins Only)</i></blockquote>\n\n"
        "<code>/auth [user]</code> — ✅ Authorize a user\n"
        "<code>/unauth [user]</code> — ❌ Remove authorization\n"
        "<code>/authlist</code> — 📋 Authorized users\n"
        "<code>/ban [user]</code> — 🔨 Ban from bot\n"
        "<code>/unban [user]</code> — ✅ Unban a user\n\n"
        "<i>Owner commands are hidden from this menu.</i>"
    ),
    "mode": (
        "<blockquote>🔴 <b>Mode Settings</b></blockquote>\n\n"
        "<code>/autoplay on</code> — 🤖 Enable AutoPlay\n"
        "<code>/autoplay off</code> — 🚫 Disable AutoPlay\n"
        "<code>/loop</code> — 🔂 Song loop mode\n"
        "<code>/loopall</code> — 🔁 Queue loop mode\n"
        "<code>/noloop</code> — ➡️ No loop"
    ),
    "other": (
        "<blockquote>🔴 <b>Other Commands</b></blockquote>\n\n"
        "<code>/start</code> — 🚀 Show welcome message\n"
        "<code>/help</code> — 📖 Show this menu\n"
        "<code>/about</code> — ℹ️ About the bot\n"
        "<code>/stats</code> — 📊 Bot statistics\n"
        "<code>/ping</code> — 🏓 Bot ping"
    ),
}

HELP_MAIN_TEXT = (
    "<blockquote>📖 <b>MELODY — Help Menu</b></blockquote>\n\n"
    "<i>Choose a command category below.</i>\n"
    "<i>All commands work with</i> <code>/</code>\n\n"
    "<blockquote>"
    "🟢 <b>Green</b> = Music &amp; Play actions\n"
    "🔵 <b>Blue</b>  = Info &amp; Settings\n"
    "🔴 <b>Red</b>   = Controls &amp; Admin"
    "</blockquote>"
)

# ─── Keyboard: 3-column grid (reference image style) ─────────────────────────

def main_help_kb() -> InlineKeyboardMarkup:
    """3-column layout with color-coded emoji like the reference image."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢  Play",     callback_data="help_play"),
            InlineKeyboardButton("🔵  Queue",    callback_data="help_queue"),
            InlineKeyboardButton("🔴  Controls", callback_data="help_controls"),
        ],
        [
            InlineKeyboardButton("🔵  Loop",     callback_data="help_loop"),
            InlineKeyboardButton("🔵  Ping",     callback_data="help_ping"),
            InlineKeyboardButton("🟢  Seek",     callback_data="help_seek"),
        ],
        [
            InlineKeyboardButton("🔵  Volume",   callback_data="help_volume"),
            InlineKeyboardButton("🔵  Lyrics",   callback_data="help_lyrics"),
            InlineKeyboardButton("🔴  Admin",    callback_data="help_admin"),
        ],
        [
            InlineKeyboardButton("🟢  Speed",    callback_data="help_volume"),
            InlineKeyboardButton("🔴  Mode",     callback_data="help_mode"),
            InlineKeyboardButton("🔴  Other",    callback_data="help_other"),
        ],
        [
            InlineKeyboardButton(
                "🔵  ➕ Add to Group",
                url=f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}?startgroup=true",
            ),
        ],
        [
            InlineKeyboardButton("🔴  ⊛ CLOSE ⊛", callback_data="help_close"),
        ],
    ])


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴  ⊛ BACK ⊛", callback_data="help_main"),
        ],
    ])


# ─── Handlers ─────────────────────────────────────────────────────────────────

@bot.on_message(filters.command("help"))
@error_handler
async def help_cmd(client: Client, message: Message):
    await message.reply(
        HELP_MAIN_TEXT,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=main_help_kb(),
    )


@bot.on_callback_query(filters.regex(r"^help_(.+)$"))
@error_handler
async def help_cb(client: Client, cb: CallbackQuery):
    key = cb.data.split("help_")[1]

    if key == "main":
        await cb.message.edit_text(
            HELP_MAIN_TEXT,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=main_help_kb(),
        )
    elif key == "close":
        try:
            await cb.message.delete()
        except Exception:
            pass
    elif key in HELP_PAGES:
        await cb.message.edit_text(
            HELP_PAGES[key],
            parse_mode=enums.ParseMode.HTML,
            reply_markup=back_kb(),
        )
    await cb.answer()
