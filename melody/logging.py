"""
📋 Logging setup — errors go to LOG_GROUP_ID only, never to users
"""
import html
import logging
import colorlog
import traceback
from melody.config import Config

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
        msg = f"<b>⚠️ Melody Error Log</b>\n\n<code>{safe_text}</code>"
        if exc:
            tb = traceback.format_exc()
            safe_tb = html.escape(tb[:3000])
            msg += f"\n\n<pre>{safe_tb}</pre>"
        await bot.send_message(Config.LOG_GROUP_ID, msg, parse_mode="html")
    except Exception:
        LOGGER.error("Failed to send log to group: %s", text)
