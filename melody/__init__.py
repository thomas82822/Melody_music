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
    )
    assistant = Client(
        "MelodyAssistant",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        session_string=Config.STRING_SESSION,
    )
    return bot, assistant
