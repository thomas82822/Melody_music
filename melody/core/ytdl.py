"""
🎵 YouTube downloader — yt-dlp wrapper
"""
import asyncio
import base64
import glob
import os
import re
from yt_dlp import YoutubeDL
from melody.config import Config
from melody.logging import LOGGER, send_error_log


COOKIES_FILE = "/tmp/melody_yt_cookies.txt"


def _write_cookies():
    """Decode base64 YT_COOKIES and write to file if provided."""
    if Config.YT_COOKIES:
        try:
            decoded = base64.b64decode(Config.YT_COOKIES).decode("utf-8", errors="replace")
            with open(COOKIES_FILE, "w") as f:
                f.write(decoded)
        except Exception as e:
            LOGGER.warning("Could not decode YT_COOKIES: %s", e)


_write_cookies()


def _ydl_opts(audio_only: bool = True) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": "bestaudio/best" if audio_only else "best[height<=720]",
        "postprocessors": [],
    }
    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    return opts


async def search_youtube(query: str, limit: int = 5) -> list[dict]:
    """Search YouTube and return a list of results."""
    def _search():
        opts = {**_ydl_opts(), "default_search": f"ytsearch{limit}", "extract_flat": True}
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(query, download=False)
            return info.get("entries", [])

    try:
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, _search)
        return [
            {
                "id": e.get("id", ""),
                "title": e.get("title", "Unknown"),
                "duration": e.get("duration", 0),
                "url": f"https://www.youtube.com/watch?v={e.get('id', '')}",
                "thumbnail": e.get("thumbnail") or f"https://i.ytimg.com/vi/{e.get('id','')}/hqdefault.jpg",
                "uploader": e.get("uploader", "Unknown"),
            }
            for e in results
            if e.get("id")
        ]
    except Exception as exc:
        await send_error_log("search_youtube failed", exc)
        return []


async def get_video_info(url_or_query: str) -> dict | None:
    """Get info for a single video (or first search result)."""
    is_url = re.match(r"https?://", url_or_query)
    query = url_or_query if is_url else f"ytsearch1:{url_or_query}"

    def _info():
        opts = {**_ydl_opts(), "extract_flat": False}
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if "entries" in info:
                info = info["entries"][0]
            return info

    try:
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(None, _info)
        return {
            "id": info.get("id", ""),
            "title": info.get("title", "Unknown"),
            "duration": info.get("duration", 0),
            "url": info.get("webpage_url") or f"https://www.youtube.com/watch?v={info.get('id','')}",
            "stream_url": "",  # not used; audio is downloaded at play time via download_audio()
            "thumbnail": info.get("thumbnail") or f"https://i.ytimg.com/vi/{info.get('id','')}/hqdefault.jpg",
            "uploader": info.get("uploader", "Unknown"),
        }
    except Exception as exc:
        await send_error_log("get_video_info failed", exc)
        return None


async def download_audio(video_id: str) -> str:
    """Download audio for a video_id to /tmp/ and return the local file path.

    Uses a cache: if the file is already downloaded, returns the cached path.
    Files are deleted by call.py after each track finishes to save /tmp space.
    """
    # Check cache first
    cached = glob.glob(f"/tmp/melody_{video_id}.*")
    if cached:
        return cached[0]

    url = f"https://www.youtube.com/watch?v={video_id}"
    outtmpl = f"/tmp/melody_{video_id}.%(ext)s"

    def _download():
        opts = {
            **_ydl_opts(audio_only=True),
            "outtmpl": outtmpl,
            "extract_flat": False,
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    loop = asyncio.get_running_loop()
    filepath = await loop.run_in_executor(None, _download)

    # prepare_filename may not include the actual ext if postprocessing renamed it
    if not os.path.exists(filepath):
        found = glob.glob(f"/tmp/melody_{video_id}.*")
        if found:
            filepath = found[0]
        else:
            raise FileNotFoundError(f"Downloaded file not found for video_id={video_id}")

    return filepath


async def get_related_videos(video_id: str, exclude_ids: list[str] = None) -> list[dict]:
    """Fetch related videos for autoplay (skip excluded IDs)."""
    exclude = set(exclude_ids or [])

    def _related():
        url = f"https://www.youtube.com/watch?v={video_id}"
        opts = {**_ydl_opts(), "extract_flat": True, "playlist_items": "1:10"}
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("entries", []) if info else []

    try:
        loop = asyncio.get_running_loop()
        entries = await loop.run_in_executor(None, _related)
        results = []
        for e in entries:
            vid = e.get("id", "")
            if vid and vid not in exclude:
                results.append({
                    "id": vid,
                    "title": e.get("title", "Unknown"),
                    "duration": e.get("duration", 0),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "thumbnail": e.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                    "uploader": e.get("uploader", "Unknown"),
                })
        return results
    except Exception as exc:
        await send_error_log("get_related_videos failed", exc)
        return []
