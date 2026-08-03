"""
📋 Logging setup — errors go to LOG_GROUP_ID only, never to users
"""
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
    """Send error traceback to LOG_GROUP_ID only — never to users."""
    try:
        from melody import bot
        msg = f"**⚠️ Melody Error Log**\n\n`{text}`"
        if exc:
            tb = traceback.format_exc()
            msg += f"\n\n```\n{tb[:3000]}\n```"
        await bot.send_message(Config.LOG_GROUP_ID, msg)
    except Exception:
        LOGGER.error("Failed to send log to group: %s", text)
