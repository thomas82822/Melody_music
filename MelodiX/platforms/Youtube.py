#
# Copyright (C) 2021-2022 by TheY_CaIl_mE_OG@Github, < https://github.com/TheY_CaIl_mE_OG >.
#
# This file is part of < https://github.com/thomas82822/Melody_music > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/thomas82822/Melody_music/blob/master/LICENSE >
#
# All rights reserved.
#
# ── YouTube-only with Cookies support ────────────────────────
# Set COOKIES env var in Heroku with the full contents of your
# cookies.txt (Netscape format) to bypass age-gates & restrictions.

import asyncio
import os
import re
import tempfile
from typing import Union

import aiohttp
import yt_dlp
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

import config
from MelodiX.utils.database import is_on_off
from MelodiX.utils.formatters import time_to_seconds


# ── Cookie helper ─────────────────────────────────────────────
def _get_cookiefile() -> str | None:
    """
    Write COOKIES env var (Netscape cookies.txt format) to a
    temp file and return its path.  Returns None if not set.
    """
    raw = os.getenv("COOKIES", "").strip()
    if not raw:
        return None
    try:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="yt_cookies_"
        )
        tmp.write(raw)
        tmp.flush()
        tmp.close()
        return tmp.name
    except Exception:
        return None


def _ydl_opts_base(cookiefile: str | None = None) -> dict:
    """Base yt-dlp options, with cookies injected if available."""
    opts = {
        "quiet": True,
        "no_warnings": True,
    }
    if cookiefile:
        opts["cookiefile"] = cookiefile
    return opts


async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in errorz.decode("utf-8").lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == "url":
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == "text_link":
                        return entity.url
        if offset in (None,):
            return None
        return text[offset: offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            if str(duration_min) == "None":
                duration_sec = 0
            else:
                duration_sec = int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
        return title

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            duration = result["duration"]
        return duration

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return thumbnail

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "-g",
            "-f",
            "best[height<=?720][width<=?1280]",
            f"{link}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            return stdout.decode().split("\n")[0]
        else:
            return None

    async def playlist(
        self, link, limit, user_id, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        playlist = await shell_cmd(
            f'yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --compat-options no-youtube-unavailable-videos "{link}"'
        )
        result = playlist.split("\n")
        video_ids = [x for x in result if x]
        return video_ids, link

    async def track(
        self, link: str, videoid: Union[bool, str] = None
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, vidid, yturl, thumbnail

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next())["result"]
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    # ── Download with cookies ─────────────────────────────────
    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link
        loop = asyncio.get_event_loop()

        # Prepare cookies file once for this download
        cookiefile = _get_cookiefile()

        def base_opts():
            opts = _ydl_opts_base(cookiefile)
            opts.update({
                "retries": 3,
                "fragment_retries": 10,
                "ignoreerrors": False,
                "logtostderr": False,
                "nooverwrites": False,
            })
            return opts

        def audio_dl():
            ydl_opts = base_opts()
            ydl_opts.update({
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "prefer_ffmpeg": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
            x = yt_dlp.YoutubeDL(ydl_opts)
            info = x.extract_info(link, download=True)
            return os.path.join("downloads", f"{info['id']}.mp3")

        def video_dl():
            ydl_opts = base_opts()
            ydl_opts.update({
                "format": "best[height<=720]+bestaudio/best[height<=720]",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "prefer_ffmpeg": True,
            })
            x = yt_dlp.YoutubeDL(ydl_opts)
            info = x.extract_info(link, download=True)
            return os.path.join("downloads", f"{info['id']}.{info['ext']}")

        def song_audio_dl():
            ydl_opts = base_opts()
            fpath = f"downloads/{title}.mp3"
            ydl_opts.update({
                "format": "bestaudio/best",
                "outtmpl": f"downloads/{title}.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "prefer_ffmpeg": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
            x = yt_dlp.YoutubeDL(ydl_opts)
            x.download([link])

        def song_video_dl():
            ydl_opts = base_opts()
            fpath = f"downloads/{title}.mp4"
            ydl_opts.update({
                "format": "best[height<=720]+bestaudio/best",
                "outtmpl": f"downloads/{title}.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "prefer_ffmpeg": True,
            })
            x = yt_dlp.YoutubeDL(ydl_opts)
            x.download([link])

        if songvideo:
            await loop.run_in_executor(None, song_video_dl)
            fpath = f"downloads/{title}.mp4"
            return fpath, True
        elif songaudio:
            await loop.run_in_executor(None, song_audio_dl)
            fpath = f"downloads/{title}.mp3"
            return fpath, True
        elif video:
            if await is_on_off(config.YTDOWNLOADER):
                downloaded_file = await loop.run_in_executor(None, video_dl)
                direct = True
            else:
                # Stream directly via URL (no download)
                cookie_args = []
                if cookiefile:
                    cookie_args = ["--cookies", cookiefile]
                proc = await asyncio.create_subprocess_exec(
                    "yt-dlp",
                    "-g",
                    "-f",
                    "best[height<=?720][width<=?1280]",
                    *cookie_args,
                    f"{link}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    downloaded_file = stdout.decode().split("\n")[0]
                    direct = None
                else:
                    return None, None
        else:
            downloaded_file = await loop.run_in_executor(None, audio_dl)
            direct = True

        return downloaded_file, direct
