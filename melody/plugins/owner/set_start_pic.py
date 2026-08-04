"""
🖼️ /setpic — Set custom start/welcome picture (owner only)
   /delpic  — Remove custom start picture (owner only)
"""
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.config import Config
from utils.decorators import owner_only, error_handler

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets")
BG_START = os.path.join(ASSETS, "bg_start.png")


def _ensure_assets():
    os.makedirs(ASSETS, exist_ok=True)


@bot.on_message(filters.command("setpic") & filters.private)
@owner_only
@error_handler
async def setpic_cmd(client: Client, message: Message):
    """
    Usage: Send a photo with caption /setpic
    OR reply to a photo with /setpic
    """
    photo = None

    # Case 1: Message itself has a photo
    if message.photo:
        photo = message.photo

    # Case 2: Reply to a photo message
    if not photo and message.reply_to_message and message.reply_to_message.photo:
        photo = message.reply_to_message.photo

    if not photo:
        return await message.reply(
            "🖼️ **Set Start Picture**\n\n"
            "Send a photo with caption `/setpic`\n"
            "or reply to a photo with `/setpic`"
        )

    msg = await message.reply("⏳ Downloading and saving image...")

    try:
        _ensure_assets()
        # Download photo to assets/bg_start.png
        file_path = await client.download_media(photo.file_id, file_name=BG_START)

        await msg.edit(
            "✅ **Start picture updated!**\n\n"
            "The new image will be shown on the next `/start` command."
        )
    except Exception as e:
        await msg.edit(f"❌ **Failed to save image.**\n`{e}`")


@bot.on_message(filters.command("delpic") & filters.private)
@owner_only
@error_handler
async def delpic_cmd(client: Client, message: Message):
    """Remove the custom start picture."""
    if os.path.exists(BG_START):
        os.remove(BG_START)
        await message.reply(
            "🗑️ **Start picture removed.**\n"
            "The bot will now use text-only start messages."
        )
    else:
        await message.reply("ℹ️ No custom start picture is set.")
