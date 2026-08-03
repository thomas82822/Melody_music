"""
🎶 Melody — Telegram Music Bot
"""
import asyncio
import logging
from pyrogram import Client
from melody.config import Config

# Initialize bot client
bot = Client(
    "MelodyBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="melody/plugins"),
)

# Initialize assistant (userbot) client
assistant = Client(
    "MelodyAssistant",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    session_string=Config.STRING_SESSION,
)
