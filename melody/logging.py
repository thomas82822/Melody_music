"""
📋 Logging setup — errors go to LOG_GROUP_ID only, never to users
"""
import html
import logging
import colorlog
import traceback
from pyrogram import enums
from melody.config import Config
from strings.themes import fancy

# Formatter
fmt = colorlog.ColoredFormatter(
    "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s: %(message)s",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
)

handler = logging.StreamHandler()
handler.setFormatter(fmt)

logging.basicConfig(level=logging.INFO, handlers=[handler])
LOGGER = logging.getLogger("Melody")


async def log_activity(text: str):
    """
    A2Z activity logger — sends every notable bot action (not just errors) to
    LOG_GROUP_ID: commands used, songs played, joins/leaves, admin actions,
    ban/auth changes, startup/shutdown, etc.

    Kept completely separate from send_error_log() so a logging failure here
    never raises into command handlers. Never blocks the caller for long —
    callers should fire this with asyncio.create_task() when on a latency
    sensitive path (e.g. /play).
    """
    try:
        from melody import bot
        from melody.config import Config
        if not Config.LOG_GROUP_ID:
            return
        await bot.send_message(
            Config.LOG_GROUP_ID,
            text,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception as exc:
        LOGGER.debug("log_activity failed to deliver: %s | text=%s", exc, text)


async def send_error_log(text: str, exc: Exception = None):
    """Send error traceback to LOG_GROUP_ID only — never to users.

    BUG FIX: Use HTML parse mode instead of Markdown to avoid
    ENTITY_BOUNDS_INVALID errors when the error text itself contains
    backticks, asterisks, or other Markdown special characters.
    html.escape() ensures angle brackets, ampersands, etc. don't
    break the HTML entity parser either.
    """
    try:
        from melody import bot
        safe_text = html.escape(str(text))
        msg = f"<b>⚠️ {fancy('Melody Error Log')}</b>\n\n<code>{safe_text}</code>"
        if exc:
            tb = traceback.format_exc()
            safe_tb = html.escape(tb[:3000])
            msg += f"\n\n<pre>{safe_tb}</pre>"
        await bot.send_message(Config.LOG_GROUP_ID, msg, parse_mode=enums.ParseMode.HTML)
    except Exception as delivery_exc:
        # BUG FIX: this used to pass `exc_info=exc` — the *original* error
        # being reported, not the exception raised by send_message() itself.
        # That hid the real delivery failure (bad parse_mode, peer not
        # found, network issue, etc.) behind an unrelated traceback, making
        # "Failed to send log to group" impossible to actually debug.
        # Log both: the delivery failure (with its own traceback) and the
        # original error text/traceback that failed to reach LOG_GROUP_ID.
        LOGGER.error("Failed to send log to group: %s", text, exc_info=delivery_exc)
        if exc:
            LOGGER.error("Original error that failed to deliver: %r", exc, exc_info=exc)
