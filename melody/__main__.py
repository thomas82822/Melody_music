"""
🎶 Melody Bot — Entry point
FIXES:
  - Plugins loaded BEFORE bot.start() so handlers register correctly
  - Slash commands registered via set_my_commands() on startup
  - Detailed log channel message with plugin count and system info
"""
import asyncio
import importlib
import pkgutil
import platform
import sys
import uvloop
from melody.logging import LOGGER
from melody.config import Config


def validate_config():
    required = ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_DB_URI", "STRING_SESSION"]
    missing = [k for k in required if not getattr(Config, k, None)]
    if missing:
        LOGGER.critical("Missing required env vars: %s", ", ".join(missing))
        raise SystemExit(1)


def load_plugins():
    """
    Load all plugins by walking melody.plugins using the package's __path__
    (absolute path) — avoids Pyrogram's relative-path auto-loader which
    fails to resolve on Heroku dyno restarts.
    """
    import melody.plugins  # ensure parent package is imported first

    loaded = 0
    failed = 0
    failed_names = []

    for finder, module_name, is_pkg in pkgutil.walk_packages(
        path=melody.plugins.__path__,
        prefix=melody.plugins.__name__ + ".",
        onerror=lambda name: LOGGER.warning("Plugin walk error: %s", name),
    ):
        if is_pkg:
            continue  # skip __init__ packages, load leaf modules only
        try:
            importlib.import_module(module_name)
            LOGGER.debug("Loaded plugin: %s", module_name)
            loaded += 1
        except Exception as exc:
            LOGGER.error("Failed to load plugin %s: %s", module_name, exc)
            failed += 1
            failed_names.append(module_name.split(".")[-1])

    LOGGER.info("Plugins loaded: %d OK, %d failed", loaded, failed)
    return loaded, failed, failed_names


async def warm_peer_cache(client, label: str):
    """
    BUG FIX: Heroku dynos have an ephemeral filesystem, so Pyrogram's local
    SQLite peer cache is wiped on every restart/redeploy. Until a chat's
    peer is resolved again, ANY incoming update from that chat makes
    Pyrogram's internal handle_updates() raise
    'ValueError: Peer id invalid: ...' before your command handlers ever
    run — so commands look like they do nothing. Iterating dialogs once
    on startup re-resolves every chat the account is already in and
    prevents this.
    """
    try:
        count = 0
        async for _ in client.get_dialogs():
            count += 1
        LOGGER.info("%s: warmed peer cache for %d chats", label, count)
    except Exception as exc:
        LOGGER.warning("%s: could not warm peer cache: %s", label, exc)


async def register_slash_commands(bot):
    """Register all slash commands with BotFather via set_my_commands()."""
    from pyrogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats

    # Commands shown in all groups
    group_commands = [
        BotCommand("play",      "▶️ Play a song from YouTube"),
        BotCommand("vplay",     "📹 Play a video stream"),
        BotCommand("pause",     "⏸ Pause playback"),
        BotCommand("resume",    "▶️ Resume playback"),
        BotCommand("skip",      "⏭ Skip current song"),
        BotCommand("stop",      "⏹ Stop music & clear queue"),
        BotCommand("queue",     "📋 Show current queue"),
        BotCommand("np",        "🎵 Now playing info"),
        BotCommand("volume",    "🔊 Set volume (1-200)"),
        BotCommand("mute",      "🔇 Mute playback"),
        BotCommand("unmute",    "🔊 Unmute playback"),
        BotCommand("loop",      "🔂 Loop current song"),
        BotCommand("loopall",   "🔁 Loop entire queue"),
        BotCommand("noloop",    "➡️ Disable loop"),
        BotCommand("shuffle",   "🔀 Shuffle queue"),
        BotCommand("clearqueue","🗑 Clear the queue"),
        BotCommand("remove",    "❌ Remove song from queue"),
        BotCommand("seek",      "⏩ Seek to position (seconds)"),
        BotCommand("speed",     "⚡ Set playback speed (0.5-2.0)"),
        BotCommand("search",    "🔍 Search YouTube"),
        BotCommand("lyrics",    "🎤 Get song lyrics"),
        BotCommand("autoplay",  "🤖 Toggle autoplay"),
        BotCommand("auth",      "👑 Authorize a user"),
        BotCommand("unauth",    "🚫 Remove user authorization"),
        BotCommand("authlist",  "📋 List authorized users"),
        BotCommand("ban",       "🔨 Ban user from bot"),
        BotCommand("unban",     "✅ Unban user"),
        BotCommand("ping",      "🏓 Check bot latency"),
        BotCommand("stats",     "📊 Bot statistics"),
        BotCommand("help",      "📖 Help menu"),
    ]

    # Commands shown in private chats (fewer — no music cmds)
    private_commands = [
        BotCommand("start",     "🎶 Start Melody"),
        BotCommand("help",      "📖 Help & command list"),
        BotCommand("ping",      "🏓 Check bot latency"),
        BotCommand("stats",     "📊 Bot statistics"),
        BotCommand("about",     "ℹ️ About Melody"),
    ]

    try:
        await bot.set_bot_commands(group_commands, scope=BotCommandScopeAllGroupChats())
        await bot.set_bot_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
        LOGGER.info("Slash commands registered: %d group, %d private",
                    len(group_commands), len(private_commands))
    except Exception as exc:
        LOGGER.warning("Could not register slash commands: %s", exc)


async def send_startup_log(bot, loaded: int, failed: int, failed_names: list):
    """Send a detailed startup message to the log channel."""
    if not Config.LOG_GROUP_ID:
        return
    try:
        me = await bot.get_me()
        py_ver = platform.python_version()
        import pyrogram
        pyrogram_ver = pyrogram.__version__

        status_line = f"✅ {loaded} plugins OK" + (
            f", ❌ {failed} failed: `{'`, `'.join(failed_names)}`" if failed else ""
        )

        text = (
            "╔══════════════════════════════╗\n"
            "║   🎶  **MELODY IS LIVE!**     ║\n"
            "╚══════════════════════════════╝\n\n"
            f"🤖 **Bot:** @{me.username} (`{me.id}`)\n"
            f"🐍 **Python:** `{py_ver}`\n"
            f"📦 **Pyrogram:** `{pyrogram_ver}`\n\n"
            f"🔌 **Plugins:** {status_line}\n"
            f"🌐 **Platform:** `{platform.system()} {platform.release()}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ All systems operational. Ready to receive commands!"
        )
        await bot.send_message(Config.LOG_GROUP_ID, text)
    except Exception as exc:
        LOGGER.warning("Could not send startup log: %s", exc)


async def main():
    validate_config()

    # Load all plugins BEFORE starting clients so decorators register handlers
    loaded, failed, failed_names = load_plugins()
    LOGGER.info("All plugins loaded.")

    from melody import bot, assistant
    from melody.core.call import start_call_py

    LOGGER.info("Starting Melody Music Bot...")

    await bot.start()
    LOGGER.info("Bot client started.")

    await assistant.start()
    LOGGER.info("Assistant client started.")

    # Re-resolve peers for chats we're already in (see warm_peer_cache docstring)
    await warm_peer_cache(bot, "bot")
    await warm_peer_cache(assistant, "assistant")

    await start_call_py()
    LOGGER.info("PyTgCalls started.")

    # Register slash commands with BotFather
    await register_slash_commands(bot)

    # Detailed startup log to log channel
    await send_startup_log(bot, loaded, failed, failed_names)

    LOGGER.info("🎶 Melody is live!")
    await asyncio.Event().wait()  # Keep running


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
