"""
📋 /help — category help menu.

Colors match the reference screenshot exactly (Admin/Auth/Loop/Ping/Shuffle
= blue, C-Play/Play/Song/Other = red, Seek/Speed/Mode = green) — but real
button backgrounds are only possible via the Mini App (`web_app/menu.html`),
since the Bot API can't color a normal chat button. When `WEBAPP_URL` is
configured, `/help` opens that colored grid; otherwise it falls back to a
plain (uncolored) native keyboard so the command still works.
"""
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    WebAppInfo,
)
from melody import bot
from melody.config import Config
from utils.decorators import error_handler
from strings.themes import fancy
from strings.webmenu import build_webapp_menu, MenuButton

# ─── Help page text (HTML) ────────────────────────────────────────────────────

HELP_PAGES = {
    "play": (
        "<blockquote>🟢 <b>Play Commands</b></blockquote>\n\n"
        "<code>/play [song/url]</code> — ▶️ Play from YouTube\n"
        "<code>/vplay [song/url]</code> — 🎬 Video stream\n"
        "<code>/playforce [song/url]</code> — ⚡ Force-play now (skips queue)\n"
        "<code>/vplayforce [song/url]</code> — ⚡ Force-play video now\n"
        "<code>/playlist [playlist url]</code> — 📃 Queue a whole playlist\n"
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
        "<code>/stop</code> <code>/end</code> — ⏹ Stop &amp; clear queue\n"
        "<code>/seek [sec]</code> — ⏩ Seek forward\n"
        "<code>/seekback [sec]</code> — ⏪ Seek backward\n"
        "<code>/rewind [sec]</code> — ⏪ Alias of /seekback\n"
        "<code>/np</code> — 🎶 Now playing info"
    ),
    "cplay": (
        "<blockquote>🟣 <b>Channel Play</b></blockquote>\n\n"
        "Use these directly inside a channel that has a voice chat — the "
        "bot streams straight into the channel's own voice chat.\n\n"
        "<code>/cplay [song/url]</code> — ▶️ Play in this channel\n"
        "<code>/cvplay [song/url]</code> — 🎬 Video stream in this channel\n"
        "<code>/cpause</code> — ⏸ Pause\n"
        "<code>/cresume</code> — ▶️ Resume\n"
        "<code>/cskip</code> — ⏭ Skip\n"
        "<code>/cstop</code> — ⏹ Stop &amp; clear queue\n\n"
        "<i>Only channel admins (or authorized users) can use these.</i>"
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
        "<code>/seek [seconds]</code> — ⏩ Jump to an absolute position\n"
        "<code>/seekback [seconds]</code> — ⏪ Go back N seconds from now\n"
        "<code>/rewind [seconds]</code> — ⏪ Alias of /seekback\n\n"
        "<i>Example: /seek 30 → jumps to 0:30. /seekback 15 → 15s earlier.</i>"
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
    f"<blockquote>📖 <b>{fancy('MELODY')} — Help Menu</b></blockquote>\n\n"
    "<i>Choose the category for which you wanna get help.</i>\n"
    "<i>All commands can be used with</i> <code>/</code>"
)

# ─── Category grid — same layout/colors as the reference screenshot ─────────
# Row 1: Admin(blue) Auth(blue) C-Play(red)
# Row 2: Loop(blue) Ping(blue) Play(red)
# Row 3: Shuffle(blue) Seek(green) Song(red)
# Row 4: Speed(green) Mode(green) Other(red)
_CATEGORY_ROWS = [
    [MenuButton("Admin", "blue", "admin"), MenuButton("Auth", "blue", "admin"), MenuButton("C-Play", "red", "cplay")],
    [MenuButton("Loop", "blue", "loop"), MenuButton("Ping", "blue", "ping"), MenuButton("Play", "red", "play")],
    [MenuButton("Shuffle", "blue", "queue"), MenuButton("Seek", "green", "seek"), MenuButton("Song", "red", "play")],
    [MenuButton("Speed", "green", "volume"), MenuButton("Mode", "green", "mode"), MenuButton("Other", "red", "other")],
]


def _category_webapp_url() -> str | None:
    return build_webapp_menu(
        menu_id="help",
        title="Melody — Help Menu",
        subtitle="Choose a category to see its commands",
        rows=_CATEGORY_ROWS,
    )


def main_help_kb() -> InlineKeyboardMarkup:
    """Help entry point. Opens the colored Mini App grid when a Mini App is
    configured (`WEBAPP_URL`); otherwise falls back to plain native buttons
    with the same categories/order, without any fake color emoji."""
    webapp_url = _category_webapp_url()

    rows = []
    if webapp_url:
        rows.append([
            InlineKeyboardButton("🎨 Open Category Menu", web_app=WebAppInfo(url=webapp_url)),
        ])
    else:
        rows.extend([
            [
                InlineKeyboardButton("Admin", callback_data="help_admin"),
                InlineKeyboardButton("Auth", callback_data="help_admin"),
                InlineKeyboardButton("C-Play", callback_data="help_cplay"),
            ],
            [
                InlineKeyboardButton("Loop", callback_data="help_loop"),
                InlineKeyboardButton("Ping", callback_data="help_ping"),
                InlineKeyboardButton("Play", callback_data="help_play"),
            ],
            [
                InlineKeyboardButton("Shuffle", callback_data="help_queue"),
                InlineKeyboardButton("Seek", callback_data="help_seek"),
                InlineKeyboardButton("Song", callback_data="help_play"),
            ],
            [
                InlineKeyboardButton("Speed", callback_data="help_volume"),
                InlineKeyboardButton("Mode", callback_data="help_mode"),
                InlineKeyboardButton("Other", callback_data="help_other"),
            ],
        ])

    rows.append([
        InlineKeyboardButton(
            "➕ Add to Group",
            url=f"https://t.me/{Config.BOT_USERNAME.lstrip('@')}?startgroup=true",
        ),
    ])
    rows.append([
        InlineKeyboardButton("✵ CLOSE ✵", callback_data="help_close"),
    ])
    return InlineKeyboardMarkup(rows)


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✵ BACK ✵", callback_data="help_main"),
        ],
    ])


def render_help_category(key: str):
    """Shared renderer used by both the callback-query flow and the Mini App
    (web_app data) flow so they never drift apart. Returns (text, markup)."""
    if key == "main":
        return HELP_MAIN_TEXT, main_help_kb()
    if key in HELP_PAGES:
        return HELP_PAGES[key], back_kb()
    return None, None


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

    if key == "close":
        try:
            await cb.message.delete()
        except Exception:
            pass
        return await cb.answer()

    text, markup = render_help_category(key)
    if text:
        await cb.message.edit_text(text, parse_mode=enums.ParseMode.HTML, reply_markup=markup)
    await cb.answer()
