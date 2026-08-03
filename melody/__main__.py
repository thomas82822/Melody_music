"""
🎶 Melody Bot — Entry point
"""
import asyncio
import uvloop
from melody.logging import LOGGER
from melody.config import Config


def validate_config():
    required = ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_DB_URI", "STRING_SESSION"]
    missing = [k for k in required if not getattr(Config, k, None)]
    if missing:
        LOGGER.critical("Missing required env vars: %s", ", ".join(missing))
        raise SystemExit(1)


async def main():
    validate_config()

    from melody import bot, assistant
    from melody.core.call import start_call_py

    LOGGER.info("Starting Melody Music Bot...")

    await bot.start()
    LOGGER.info("Bot client started.")

    await assistant.start()
    LOGGER.info("Assistant client started.")

    await start_call_py()
    LOGGER.info("PyTgCalls started.")

    # Notify owner (silently — no user-visible info)
    try:
        from melody.config import Config
        await bot.send_message(Config.LOG_GROUP_ID, "🎶 **Melody started successfully!**")
    except Exception:
        pass

    LOGGER.info("🎶 Melody is live!")
    await asyncio.Event().wait()  # Keep running


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
