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
from melody.logging import LOGGER, send_error_log, log_activity
from melody.core.ytdl import get_related_videos, get_video_info, download_audio
from melody.core.queue import (
    Track, set_current, set_predownloaded, pop_predownloaded, peek_predownloaded,
)
from utils.database import get_history, add_history


async def _pick_related_track(chat_id: int) -> "Track | None":
    """Ask history + YouTube's related-videos graph for the next AutoPlay pick.

    BUG FIX ("autoplay button hota hai uske baad kuch nhi hota"):
    This used to take the top related video's URL and feed it BACK through
    get_video_info() — a redundant search round-trip. get_video_info() runs
    the query through yt-dlp's ytsearch1: path, and when the InnerTube/
    Invidious fallback kicks in, the returned ``id`` / ``webpage_url`` can
    be the raw search query text (e.g. "afgan japbo") instead of a clean
    11-char YouTube video ID. That garbage then became ``track.video_id``,
    and download_audio() built the URL
    ``https://www.youtube.com/watch?v=afgan%20japbo`` — an unsupported URL
    that crashes yt-dlp every time, killing AutoPlay silently.

    get_related_videos() already returns id, title, duration, url, thumbnail,
    and uploader for each candidate, so there is no reason to re-fetch via
    get_video_info() at all. Build the Track directly from that data.

    BUG FIX ("autoplay on kiya but queue is empty dikha raha"):
    This used to return None immediately when history was empty — which
    happens on the very first song (history is only written AFTER play
    starts) or when the DB call fails. That made AutoPlay silently do
    nothing: no track was predicted, nothing was queued, and /queue showed
    "Queue is empty" even though AutoPlay was ON. Now: when history is
    empty, fall back to the currently playing track's video_id as the
    seed for related-videos lookup, so AutoPlay works from the very first
    song instead of waiting for a history entry that may never come.
    """
    from melody.core.queue import get_current

    history = await get_history(chat_id)
    exclude_ids = [h["id"] for h in history] if history else []

    if history:
        last_id = history[-1]["id"]
    else:
        current = get_current(chat_id)
        if not current or not current.video_id:
            return None
        last_id = current.video_id

    related = await get_related_videos(last_id, exclude_ids=exclude_ids)
    if not related:
        return None

    top = related[0]
    vid = top.get("id") or ""
    # Defensive guard: a valid YouTube video ID is exactly 11 chars of
    # [A-Za-z0-9_-]. If the related-videos source returned anything else
    # (a search query leaking through, an empty string, etc.), skip it
    # instead of letting a garbage ID reach download_audio().
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        LOGGER.warning("AutoPlay: skipping invalid related video_id %r", vid)
        # Try the next candidate if the first was bad.
        for cand in related[1:]:
            cand_vid = cand.get("id") or ""
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", cand_vid):
                top = cand
                vid = cand_vid
                break
        else:
            return None

    return Track(
        video_id=vid,
        title=top.get("title", "Unknown"),
        duration=top.get("duration", 0),
        stream_url="",
        thumbnail=top.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
        uploader=top.get("uploader", "Unknown"),
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
        from melody.core.call import _stream_track, play_stream, is_active, is_video_active

        track = pop_predownloaded(chat_id)
        if not track:
            track = await _pick_related_track(chat_id)
        if not track:
            return False

        # BUG FIX ("kabhi vplay kabhi play"): this used to call _stream_track
        # / play_stream with no `video` argument, always defaulting to
        # audio-only — so AutoPlay silently dropped video the moment it took
        # over from a /vplay session. If the call is still connected, keep
        # streaming in whatever mode it was actually joined in (video can't
        # be renegotiated mid-call anyway — see pre_join()'s docstring).
        # If starting a fresh call, carry over the track's own video intent.
        video = is_video_active(chat_id) if is_active(chat_id) else track.video
        track.video = video
        set_current(chat_id, track)
        if is_active(chat_id):
            await _stream_track(chat_id, track, video=video)
        else:
            await play_stream(chat_id, track, video=video)
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
