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
from utils.database import get_all_chats


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

    NOTE: only call this for the userbot/assistant client. `get_dialogs()`
    calls messages.getDialogs, which Telegram rejects for bot accounts
    with "400 BOT_METHOD_INVALID" — bots can never use this method, so
    calling it for the bot client is guaranteed to fail every startup.
    """
    try:
        count = 0
        async for _ in client.get_dialogs():
            count += 1
        LOGGER.info("%s: warmed peer cache for %d chats", label, count)
    except Exception as exc:
        LOGGER.warning("%s: could not warm peer cache: %s", label, exc)


async def warm_bot_peer_cache(bot):
    """
    BUG FIX: the bot client can't call get_dialogs() (BOT_METHOD_INVALID),
    so — unlike the assistant — it starts every restart with a completely
    empty local peer cache (Heroku wipes the session file on every
    restart/redeploy). When an update then arrives from a group chat the
    bot hasn't "seen" yet in this process, Pyrogram's own update parser
    raises an UNHANDLED `ValueError: Peer id invalid: ...` deep inside its
    dispatcher/update-parsing internals — this happens before our
    @error_handler-wrapped handlers ever run, so it's invisible in our
    logs and silently drops the update. Symptom: the bot looks fully
    "started" but never responds to any command in existing groups.

    Fix: resolve_peer() IS allowed for bots as long as the chat_id was
    seen before, so we pre-warm using the chat IDs we already persist in
    MongoDB every time the bot is added to a group (see add_chat()).
    """
    chats = None
    for attempt in range(1, 4):
        try:
            chats = await get_all_chats()
            break
        except Exception as exc:
            LOGGER.warning(
                "bot: could not load chats from DB to warm cache (attempt %d/3): %s",
                attempt, exc,
            )
            if attempt < 3:
                await asyncio.sleep(5 * attempt)

    if chats is None:
        LOGGER.warning(
            "bot: giving up warming peer cache — DB unreachable after 3 attempts. "
            "Commands in groups the bot hasn't seen yet this run may not respond "
            "until MongoDB connectivity is restored."
        )
        return

    warmed = 0
    for chat in chats:
        try:
            await bot.resolve_peer(chat["chat_id"])
            warmed += 1
        except Exception:
            pass  # bot likely left/kicked from this chat — skip it

    LOGGER.info("bot: warmed peer cache for %d/%d known chats", warmed, len(chats))


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


async def sync_log_group_peer(bot, assistant):
    """
    ROOT-CAUSE FIX for "Peer id invalid: LOG_GROUP_ID" on bot client.

    WHY IT HAPPENS
    ══════════════
    Heroku wipes every dyno's ephemeral filesystem on restart, which
    destroys Pyrogram's local SQLite session files.  Pyrogram resolves a
    raw chat ID (e.g. -1004334848663) to an InputPeerChannel only when it
    has previously cached that channel's access_hash — without it the call
    raises "Peer id invalid".  The bot cannot self-populate this cache
    because:
      • get_dialogs() → Telegram rejects it with BOT_METHOD_INVALID
      • get_chat(int_id) internally calls resolve_peer which fails the
        same way
    So the bot ALWAYS starts with an empty peer DB and ALWAYS fails to
    send to any channel it hasn't received a live update from yet.

    WHY THE LOG CHANNEL SPECIFICALLY
    ═════════════════════════════════
    The log channel is a broadcast channel (only admins can post).  The
    bot is an admin; the assistant is a subscriber.  Swapping the sender
    to the assistant fails with CHAT_ADMIN_REQUIRED.  So we must keep the
    bot as the sender — we just need to give it the access_hash.

    THE FIX
    ═══════
    The assistant already called get_dialogs() on startup and has the log
    channel's access_hash in its SQLite cache.  We call
    assistant.resolve_peer(LOG_GROUP_ID) — which succeeds — and then write
    the resulting (id, access_hash, type) tuple directly into the bot
    client's SQLite peer table via bot.storage.update_peers().  From that
    point forward, bot.resolve_peer(LOG_GROUP_ID) succeeds for this
    process lifetime, so bot.send_message() works without any incoming
    update from the channel.
    """
    if not Config.LOG_GROUP_ID:
        return
    try:
        from pyrogram.raw.types import InputPeerChannel, InputPeerChat
        peer = await assistant.resolve_peer(Config.LOG_GROUP_ID)
        if isinstance(peer, InputPeerChannel):
            # update_peers signature: list of (id, access_hash, type, username, phone)
            # `id` must be the full signed integer Pyrogram uses as the chat key,
            # i.e. -(1_000_000_000_000 + channel_id) — same value as LOG_GROUP_ID.
            await bot.storage.update_peers([
                (Config.LOG_GROUP_ID, peer.access_hash, 2, None, None)
            ])
            LOGGER.info(
                "bot: synced LOG_GROUP_ID peer (access_hash injected) from assistant cache"
            )
        else:
            # Ordinary group chat — Pyrogram resolves plain group IDs by chat_id
            # without needing an access_hash, so no injection required.
            LOGGER.debug("bot: log group is a plain group — no peer injection needed")
    except Exception as exc:
        LOGGER.warning("bot: could not sync log group peer from assistant: %s", exc)


async def send_startup_log(bot, loaded: int, failed: int, failed_names: list):
    """Send a detailed startup message to the log channel (bot client only)."""
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

    # Re-resolve peers for chats we're already in (see warm_peer_cache docstring).
    # Only the assistant/userbot account can call get_dialogs() — bots always
    # get rejected with "BOT_METHOD_INVALID", so don't waste a call on `bot`.
    await warm_peer_cache(assistant, "assistant")
    # The bot client needs its own warm-up (see warm_bot_peer_cache docstring) —
    # without it, the bot silently fails to respond in any group it hasn't
    # "seen" yet this process, which is why only the assistant worked.
    await warm_bot_peer_cache(bot)

    await start_call_py()
    LOGGER.info("PyTgCalls started.")

    # Register slash commands with BotFather
    await register_slash_commands(bot)

    # Copy log-group access_hash from assistant's warm cache into bot's
    # storage so bot.send_message(LOG_GROUP_ID) can resolve the peer.
    # Must run AFTER warm_peer_cache(assistant) above.
    await sync_log_group_peer(bot, assistant)

    # Detailed startup log to log channel (bot is channel admin — correct sender)
    await send_startup_log(bot, loaded, failed, failed_names)

    LOGGER.info("🎶 Melody is live!")
    await asyncio.Event().wait()  # Keep running


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
