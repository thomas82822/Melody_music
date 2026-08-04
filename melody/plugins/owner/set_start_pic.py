"""
🖼️ /setpic — Set custom start/welcome picture (owner only)
   /delpic  — Remove custom start picture (owner only)

FIX: After saving bg_start.png locally, the image is also pushed to the
     GitHub repository so it persists across fresh deployments/restarts.
     Set GITHUB_TOKEN + GITHUB_REPO in your .env to enable this.
     The push is best-effort — a failure is reported but does NOT block
     the local save, so the pic works immediately regardless.
"""
import asyncio
import base64
import json
import os
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from melody import bot
from melody.config import Config
from utils.decorators import owner_only, error_handler

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets")
BG_START = os.path.join(ASSETS, "bg_start.png")

# GitHub target path inside the repo
_GH_FILE_PATH = "assets/bg_start.png"
_GH_API_BASE = "https://api.github.com"


def _ensure_assets():
    os.makedirs(ASSETS, exist_ok=True)


async def _push_to_github(local_path: str) -> tuple[bool, str]:
    """
    Upload local_path to the GitHub repo via the Contents API.
    Returns (success: bool, message: str).

    Requires Config.GITHUB_TOKEN and Config.GITHUB_REPO (e.g. "user/repo").
    """
    token = Config.GITHUB_TOKEN
    repo  = Config.GITHUB_REPO
    if not token or not repo:
        return False, "GITHUB_TOKEN / GITHUB_REPO not set in .env — skipping GitHub push."

    try:
        import aiohttp
    except ImportError:
        return False, "aiohttp not installed — cannot push to GitHub."

    try:
        with open(local_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode()
    except OSError as e:
        return False, f"Could not read local file: {e}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"{_GH_API_BASE}/repos/{repo}/contents/{_GH_FILE_PATH}"

    async with aiohttp.ClientSession() as session:
        # 1. Check if the file already exists (need its SHA to update it)
        sha = None
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                sha = data.get("sha")

        # 2. Create or update the file
        payload: dict = {
            "message": "🖼️ Update bot start picture via /setpic",
            "content": content_b64,
        }
        if sha:
            payload["sha"] = sha

        async with session.put(url, headers=headers, json=payload) as resp:
            if resp.status in (200, 201):
                return True, "Image pushed to GitHub ✅"
            body = await resp.text()
            return False, f"GitHub API error {resp.status}: {body[:200]}"


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
            "🖼️ <b>Set Start Picture</b>\n\n"
            "Send a photo with caption <code>/setpic</code>\n"
            "or reply to a photo with <code>/setpic</code>",
            parse_mode=enums.ParseMode.HTML,
        )

    msg = await message.reply("⏳ Downloading and saving image...")

    try:
        _ensure_assets()
        # Download photo to assets/bg_start.png
        await client.download_media(photo.file_id, file_name=BG_START)
    except Exception as e:
        await msg.edit(f"❌ <b>Failed to save image.</b>\n<code>{e}</code>",
                       parse_mode=enums.ParseMode.HTML)
        return

    # Push to GitHub (best-effort, in background)
    gh_ok, gh_msg = await _push_to_github(BG_START)

    gh_line = (
        f"\n\n📦 <b>GitHub:</b> {gh_msg}"
        if not gh_ok
        else f"\n\n📦 <b>GitHub:</b> {gh_msg}"
    )

    await msg.edit(
        "✅ <b>Start picture updated!</b>\n\n"
        "The new image will be shown on the next <code>/start</code> command "
        "and whenever the bot is added to a new group."
        + gh_line,
        parse_mode=enums.ParseMode.HTML,
    )


@bot.on_message(filters.command("delpic") & filters.private)
@owner_only
@error_handler
async def delpic_cmd(client: Client, message: Message):
    """Remove the custom start picture."""
    if os.path.exists(BG_START):
        os.remove(BG_START)
        await message.reply(
            "🗑️ <b>Start picture removed.</b>\n"
            "The bot will now use text-only start messages.",
            parse_mode=enums.ParseMode.HTML,
        )
    else:
        await message.reply(
            "ℹ️ No custom start picture is set.",
            parse_mode=enums.ParseMode.HTML,
        )
