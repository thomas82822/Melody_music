"""
🔁 /reboot, /reload — owner only
"""
import asyncio
import os
import sys
import importlib
import pkgutil
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from utils.decorators import owner_only, error_handler
from melody.logging import LOGGER


@bot.on_message(filters.command(["reboot", "restart"]) & filters.private)
@owner_only
@error_handler
async def reboot_cmd(client: Client, message: Message):
    """Full reboot — restarts the entire process."""
    await message.reply("🔁 **Rebooting Melody...**\n_Thodi der mein wapas aaunga!_")
    await asyncio.sleep(1)
    os.execv(sys.executable, [sys.executable, "-m", "melody"])


@bot.on_message(filters.command("reload") & filters.private)
@owner_only
@error_handler
async def reload_cmd(client: Client, message: Message):
    """Hot-reload all plugins without full restart."""
    msg = await message.reply("🔄 **Reloading plugins...**")
    reloaded = []
    failed = []

    import melody.plugins as plugins_pkg

    for finder, name, ispkg in pkgutil.walk_packages(
        plugins_pkg.__path__, plugins_pkg.__name__ + "."
    ):
        try:
            mod = sys.modules.get(name)
            if mod:
                importlib.reload(mod)
                reloaded.append(name.split(".")[-1])
            else:
                importlib.import_module(name)
                reloaded.append(name.split(".")[-1])
        except Exception as e:
            LOGGER.error("Reload failed for %s: %s", name, e)
            failed.append(name.split(".")[-1])

    text = f"✅ **Reloaded {len(reloaded)} plugins**\n"
    if reloaded:
        text += f"`{'`, `'.join(reloaded[:20])}`\n"
    if failed:
        text += f"\n❌ **Failed ({len(failed)}):** `{'`, `'.join(failed)}`"

    await msg.edit(text)
