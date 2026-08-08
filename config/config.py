#
# Copyright (C) 2021-2022 by TheY_CaIl_mE_OG@Github, < https://github.com/TheY_CaIl_mE_OG >.
#
# This file is part of < https://github.com/thomas82822/Melody_music > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/thomas82822/Melody_music/blob/master/LICENSE >
#
# All rights reserved.
#
# ── YouTube-only bot. Spotify / Apple / Resso / SoundCloud removed. ──

import re
import sys
from os import getenv

from dotenv import load_dotenv
from pyrogram import filters

load_dotenv()

# ── Telegram credentials ─────────────────────────────────────
API_ID   = int(getenv("API_ID", ""))
API_HASH = getenv("API_HASH")
BOT_TOKEN = getenv("BOT_TOKEN")

# ── Database ─────────────────────────────────────────────────
# MongoDB URI — https://cloud.mongodb.com
MONGO_DB_URI = getenv("MONGO_DB_URI", None)

# ── YouTube Cookies ──────────────────────────────────────────
# Paste the full contents of your cookies.txt (Netscape format) here.
# Export from browser using "Get cookies.txt LOCALLY" extension.
# This lets yt-dlp bypass age restrictions and bot-detection.
COOKIES = getenv("COOKIES", "")

# ── Duration limits ──────────────────────────────────────────
DURATION_LIMIT_MIN = int(getenv("DURATION_LIMIT", "60"))      # minutes
DURATION_LIMIT     = DURATION_LIMIT_MIN * 60                   # seconds

SONG_DOWNLOAD_DURATION = int(getenv("SONG_DOWNLOAD_DURATION_LIMIT", "180"))

# ── Log Group ────────────────────────────────────────────────
LOG_GROUP_ID = int(getenv("LOG_GROUP_ID", ""))

# ── Bot Name ─────────────────────────────────────────────────
MUSIC_BOT_NAME = getenv("MUSIC_BOT_NAME", "MelodiX")

# ── Owner ────────────────────────────────────────────────────
OWNER_ID = list(map(int, getenv("OWNER_ID", "").split()))

# ── Heroku ───────────────────────────────────────────────────
HEROKU_API_KEY  = getenv("HEROKU_API_KEY")
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")

# ── Upstream repo ────────────────────────────────────────────
UPSTREAM_REPO   = getenv("UPSTREAM_REPO", "https://github.com/thomas82822/Melody_music")
UPSTREAM_BRANCH = getenv("UPSTREAM_BRANCH", "master")
GIT_TOKEN       = getenv("GIT_TOKEN", None)

# ── Support links ────────────────────────────────────────────
SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/MelodiXMusic_Bot")
SUPPORT_GROUP   = getenv("SUPPORT_GROUP",   "https://t.me/MelodiXMusic_Bot")

# ── Assistant behavior ───────────────────────────────────────
AUTO_LEAVING_ASSISTANT    = getenv("AUTO_LEAVING_ASSISTANT", None)
AUTO_LEAVE_ASSISTANT_TIME = int(getenv("ASSISTANT_LEAVE_TIME", "5400"))
AUTO_SUGGESTION_TIME      = int(getenv("AUTO_SUGGESTION_TIME", "5400"))
AUTO_DOWNLOADS_CLEAR      = getenv("AUTO_DOWNLOADS_CLEAR", None)
AUTO_SUGGESTION_MODE      = getenv("AUTO_SUGGESTION_MODE", None)
PRIVATE_BOT_MODE          = getenv("PRIVATE_BOT_MODE", None)

# ── Assistant string sessions ────────────────────────────────
STRING1 = getenv("STRING1", None)
STRING2 = getenv("STRING2", None)
STRING3 = getenv("STRING3", None)
STRING4 = getenv("STRING4", None)
STRING5 = getenv("STRING5", None)

# ── Download sleep timers ────────────────────────────────────
YOUTUBE_DOWNLOAD_EDIT_SLEEP  = int(getenv("YOUTUBE_EDIT_SLEEP", "3"))
TELEGRAM_DOWNLOAD_EDIT_SLEEP = int(getenv("TELEGRAM_EDIT_SLEEP", "5"))

# ── GitHub repo ──────────────────────────────────────────────
GITHUB_REPO = getenv("GITHUB_REPO", "https://github.com/thomas82822/Melody_music")

# ── File size limits (bytes) ─────────────────────────────────
TG_AUDIO_FILESIZE_LIMIT = int(getenv("TG_AUDIO_FILESIZE_LIMIT", "104857600"))   # 100 MB
TG_VIDEO_FILESIZE_LIMIT = int(getenv("TG_VIDEO_FILESIZE_LIMIT", "1073741824"))  # 1 GB

# ── Playlist settings ────────────────────────────────────────
PLAYLIST_FETCH_LIMIT = int(getenv("PLAYLIST_FETCH_LIMIT", "25"))

# ── Video mode ───────────────────────────────────────────────
VIDEO_STREAM_LIMIT = int(getenv("VIDEO_STREAM_LIMIT", "3"))
YTDOWNLOADER       = int(getenv("YTDOWNLOADER", "1"))

# ── Thumbnail images ─────────────────────────────────────────
YOUTUBE_IMG_URL  = getenv("YOUTUBE_IMG_URL",  "assets/Youtube.jpeg")
TELEGRAM_IMG_URL = getenv("TELEGRAM_IMG_URL", "assets/Audio.jpeg")
STREAM_IMG_URL   = getenv("STREAM_IMG_URL",   "assets/Stream.jpeg")
TELEGRAM_AUDIO_URL = getenv("TELEGRAM_AUDIO_URL", "assets/Audio.jpeg")
TELEGRAM_VIDEO_URL = getenv("TELEGRAM_VIDEO_URL", "assets/Video.jpeg")

# ── Banned users set (populated at runtime) ──────────────────
BANNED_USERS = filters.user()

# ── Lyrical mode ─────────────────────────────────────────────
lyrical = {}

# ── Validation ───────────────────────────────────────────────
if SUPPORT_CHANNEL and not re.match("(?:http|https)://", SUPPORT_CHANNEL):
    print("[ERROR] SUPPORT_CHANNEL must start with https://")
    sys.exit()

if SUPPORT_GROUP and not re.match("(?:http|https)://", SUPPORT_GROUP):
    print("[ERROR] SUPPORT_GROUP must start with https://")
    sys.exit()

if UPSTREAM_REPO and not re.match("(?:http|https)://", UPSTREAM_REPO):
    print("[ERROR] UPSTREAM_REPO must start with https://")
    sys.exit()

if STREAM_IMG_URL and STREAM_IMG_URL != "assets/Stream.jpeg":
    if not re.match("(?:http|https)://", STREAM_IMG_URL):
        print("[ERROR] STREAM_IMG_URL must start with https://")
        sys.exit()

if YOUTUBE_IMG_URL and YOUTUBE_IMG_URL != "assets/Youtube.jpeg":
    if not re.match("(?:http|https)://", YOUTUBE_IMG_URL):
        print("[ERROR] YOUTUBE_IMG_URL must start with https://")
        sys.exit()
