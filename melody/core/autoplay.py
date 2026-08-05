"""
🤖 AutoPlay logic — fetch related videos from history AND pre-download the
predicted next track ahead of time.

REQUIREMENT: "/autoplay on hote hi next jo bhi song rahega pehle hi download
krke rakh" — as soon as a track is live and AutoPlay is on for that chat,
predict what AutoPlay would play next and download its audio into /tmp in the
background. By the time the current song actually ends, try_autoplay() has
nothing left to wait on — the file is already sitting on disk.
"""
import html
import asyncio
from melody.logging import send_error_log, log_activity
from melody.core.ytdl import get_related_videos, get_video_info, download_audio
from melody.core.queue import (
    Track, set_current, set_predownloaded, pop_predownloaded, peek_predownloaded,
)
from utils.database import get_history, add_history


async def _pick_related_track(chat_id: int) -> "Track | None":
    """Ask history + YouTube's related-videos graph for the next AutoPlay pick."""
    history = await get_history(chat_id)
    if not history:
        return None

    last_id = history[-1]["id"]
    exclude_ids = [h["id"] for h in history]

    related = await get_related_videos(last_id, exclude_ids=exclude_ids)
    if not related:
        return None

    top = related[0]
    info = await get_video_info(top["url"])
    if not info:
        return None

    return Track(
        video_id=info["id"],
        title=info["title"],
        duration=info["duration"],
        stream_url=info["stream_url"],
        thumbnail=info["thumbnail"],
        uploader=info["uploader"],
        requester_id=0,
        requester_name="AutoPlay",
        requested_in=chat_id,
    )


async def prefetch_next(chat_id: int) -> "Track | None":
    """
    Predict + pre-download the next AutoPlay track for `chat_id`.

    Called right after a track starts playing (from call.py) whenever the
    manual queue is empty and AutoPlay is ON for that chat, AND right when
    a chat turns AutoPlay on (see autoplay_cmd.py) — "jese hi on hoga next
    song queue me add + download". Safe / cheap to call repeatedly — it
    no-ops if a pre-download is already queued. Returns the track (already
    cached to /tmp) so callers can also surface it in the visible queue.
    """
    try:
        cached = peek_predownloaded(chat_id)
        if cached:
            return cached  # already have the next one cached

        track = await _pick_related_track(chat_id)
        if not track:
            return None

        # This is the actual "download krke rakh" step — warms the /tmp
        # cache for this video_id so try_autoplay()'s download_audio() call
        # returns instantly (cache hit) instead of downloading from scratch.
        await download_audio(track.video_id)

        set_predownloaded(chat_id, track)
        return track
    except Exception as exc:
        await send_error_log(f"prefetch_next failed in {chat_id}", exc)
        return None


async def try_autoplay(chat_id: int) -> bool:
    """
    Play the next AutoPlay track for a chat — uses the pre-downloaded one
    if available, otherwise falls back to a fresh lookup+download.

    BUG FIX ("autoplay on kiya phir bhi bot VC left kar diya"): this used
    to be gated on `is_active(chat_id)` and always call `play_stream()`,
    which assumes the bot has *already left* the call. But call.py's
    `_play_next()` now calls this BEFORE leaving the voice chat (so the
    bot stays connected across the transition — no more leave→rejoin
    flicker/race). That means `is_active(chat_id)` is still True at this
    point, which used to make this function bail out immediately and do
    nothing — the real root cause of AutoPlay silently never kicking in.
    Now: if the bot is still in the call, swap the stream in place via
    `_stream_track()`; only fall back to a fresh `play_stream()` join for
    the rare case this is invoked while the bot isn't connected at all.

    Returns True if a track started playing, False if there was nothing
    to play (caller should then actually leave the call).
    """
    try:
        from melody.core.call import _stream_track, play_stream, is_active

        track = pop_predownloaded(chat_id)
        if not track:
            track = await _pick_related_track(chat_id)
        if not track:
            return False

        set_current(chat_id, track)
        if is_active(chat_id):
            await _stream_track(chat_id, track)
        else:
            await play_stream(chat_id, track)
        await add_history(chat_id, track.video_id, track.title)

        from melody import bot
        safe_title = html.escape(track.title[:60])
        await bot.send_message(
            chat_id,
            f"<blockquote>🎶 <b>AutoPlay ▶️</b> <code>{safe_title}</code>\n"
            f"<i>Melody ne sunwaya!</i>\n"
            f"🙋 Requested by: <i>AutoPlay</i></blockquote>",
            parse_mode="html",
        )
        asyncio.create_task(log_activity(
            f"🤖 <b>AutoPlay Triggered</b>\n"
            f"• Song: <code>{safe_title}</code>\n"
            f"• Chat: <code>{chat_id}</code>"
        ))

        # Immediately line up (and download) the one after this too.
        asyncio.create_task(prefetch_next(chat_id))
        return True

    except Exception as exc:
        await send_error_log(f"try_autoplay failed in {chat_id}", exc)
        return False
