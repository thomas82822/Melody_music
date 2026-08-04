"""
🔑 Configuration — reads from .env only, NEVER hardcoded
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram API credentials
    API_ID: int = int(os.environ.get("API_ID", 0))
    API_HASH: str = os.environ.get("API_HASH", "")
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
    STRING_SESSION: str = os.environ.get("STRING_SESSION", "")

    # Database
    MONGO_DB_URI: str = os.environ.get("MONGO_DB_URI", "")

    # Owner settings (alias only — real identity NEVER exposed)
    OWNER_ID: int = int(os.environ.get("OWNER_ID", 0))
    OWNER_NAME: str = os.environ.get("OWNER_NAME", "Maestro")

    # Logging
    LOG_GROUP_ID: int = int(os.environ.get("LOG_GROUP_ID", 0))

    # YouTube
    YT_COOKIES: str = os.environ.get("YT_COOKIES", "")
    # Optional residential/rotating proxy for yt-dlp requests
    # (e.g. "http://user:pass@host:port" or "socks5://user:pass@host:port").
    # Heroku dyno IPs live in well-known AWS/cloud datacenter ranges that
    # YouTube fingerprints and blocks much more aggressively than home IPs
    # — this is the real cause of "Sign in to confirm you're not a bot" /
    # "Requested format is not available" even WITH valid cookies. Routing
    # yt-dlp traffic through a residential proxy fixes both the bot-detection
    # wall and most geo-restrictions, since requests then look like they come
    # from a normal home connection instead of a Heroku/AWS datacenter IP.
    YT_PROXY: str = os.environ.get("YT_PROXY", "")

    # Lyrics
    GENIUS_API_TOKEN: str = os.environ.get("GENIUS_API_TOKEN", "")

    # Bot settings
    # 0 = unlimited song duration (Melody plays full songs, mixes, even long
    # live sets — no artificial cutoff). Set a positive number of seconds in
    # .env only if you deliberately want a cap again.
    MAX_DURATION: int = int(os.environ.get("MAX_DURATION", 0))
    AUTOPLAY: bool = os.environ.get("AUTOPLAY", "true").lower() == "true"
    BOT_USERNAME: str = os.environ.get("BOT_USERNAME", "")
    WEBAPP_URL: str = os.environ.get("WEBAPP_URL", "")

    # Welcome animated sticker (file_id of any Telegram sticker/animation)
    # Set this in .env: WELCOME_STICKER=<file_id>
    # To get a file_id: forward any sticker to your bot and use /eval to print message.sticker.file_id
    WELCOME_STICKER: str = os.environ.get("WELCOME_STICKER", "")

    # GitHub integration — used by /setpic to persist the bot's start image
    # across fresh deployments. Set GITHUB_TOKEN to a Personal Access Token
    # with repo write permissions and GITHUB_REPO to "username/reponame".
    GITHUB_TOKEN: str = os.environ.get("GITHUB_TOKEN", "")
    GITHUB_REPO: str = os.environ.get("GITHUB_REPO", "")

    # Theme colors (Modi-Meloni)
    COLORS = {
        "saffron":  "#FF6600",
        "gold":     "#FFD700",
        "green":    "#009246",
        "red":      "#CE2B37",
        "white":    "#FFFFFF",
        "dark":     "#1A0500",
        "overlay":  "rgba(0,0,0,0.55)",
    }
