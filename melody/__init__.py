"""
🎶 Melody — Telegram Music Bot

FIX (Silent crash root cause):
    `python -m melody` runs this file BEFORE any code in __main__.py executes —
    which means BEFORE validate_config() can run. The old code created Pyrogram
    Client objects here at module import time. If STRING_SESSION is empty (""),
    Pyrogram raises `ValueError: Invalid session string` during import with zero
    log output — the process just dies silently.

    Fix: expose module-level `bot` and `assistant` as None initially.
    `create_clients()` in __main__.py sets them after validate_config() passes.
"""
from pyrogram import Client

# Set by create_clients() in __main__.py — always None until then.
bot: "Client | None" = None
assistant: "Client | None" = None


def create_clients() -> tuple:
    """
    Instantiate both Pyrogram clients and store as module globals so every
    plugin can safely do `from melody import bot, assistant`.
    Must be called AFTER validate_config() succeeds in __main__.py.
    """
    global bot, assistant
    from melody.config import Config

    bot = Client(
        "MelodyBot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        # BUG FIX (⚠️ FloodWait crashing commands): Pyrogram's default
        # sleep_threshold is only 10s — any FLOOD_WAIT_X above that raises
        # FloodWait straight out of send_message/reply instead of handling
        # it, which is exactly what crashed play_cmd with a 23s wait. Raising
        # the threshold makes Pyrogram transparently `asyncio.sleep()` and
        # retry any flood wait up to this many seconds instead of raising,
        # so ordinary bursts of activity no longer surface as user-visible
        # errors. Genuinely huge waits (rare, usually account-level abuse
        # flags) still raise and are caught by error_handler/safe_send.
        sleep_threshold=60,
    )
    assistant = Client(
        "MelodyAssistant",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        session_string=Config.STRING_SESSION,
        sleep_threshold=60,
    )

    # Premium emoji everywhere: patch Client.send_message/edit_message_text/
    # send_photo so every outgoing text/caption from either client is
    # automatically wrapped with real premium custom-emoji ids (see
    # utils/emoji_patch.py for why this is done centrally instead of
    # per-plugin).
    from utils.emoji_patch import apply_emoji_patch

    apply_emoji_patch()

    return bot, assistant
