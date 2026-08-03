"""
🎶 Melody Bot — Entry point
"""
import asyncio
import importlib
import pkgutil
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

    LOGGER.info("Plugins loaded: %d OK, %d failed", loaded, failed)


async def main():
    validate_config()

    # Load all plugins BEFORE starting clients so decorators register handlers
    load_plugins()
    LOGGER.info("All plugins loaded.")

    from melody import bot, assistant
    from melody.core.call import start_call_py

    LOGGER.info("Starting Melody Music Bot...")

    await bot.start()
    LOGGER.info("Bot client started.")

    await assistant.start()
    LOGGER.info("Assistant client started.")

    await start_call_py()
    LOGGER.info("PyTgCalls started.")

    # Notify owner
    try:
        await bot.send_message(Config.LOG_GROUP_ID, "🎶 **Melody started successfully!**")
    except Exception:
        pass

    LOGGER.info("🎶 Melody is live!")
    await asyncio.Event().wait()  # Keep running


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
