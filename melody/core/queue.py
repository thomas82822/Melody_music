"""
📋 Queue management — per-chat in-memory queues with settings

FIX: format_queue() now returns HTML (not Markdown) so queue_cmd.py can
     send it with parse_mode=HTML and avoid ENTITY_BOUNDS_INVALID when song
     titles contain Markdown special characters (* _ ` [ etc.).
"""
import html
import random
from dataclasses import dataclass, field
from typing import Optional
from utils.database import get_setting, set_setting
from utils.formatters import premium_emoji, PREMIUM_EMOJI_IDS


@dataclass
class Track:
    video_id: str
    title: str
    duration: int
    stream_url: str
    thumbnail: str
    uploader: str
    requester_id: int
    requester_name: str
    requested_in: int  # chat_id
    # BUG FIX ("kabhi vplay kabhi play" — video intent silently lost): this
    # used to have no field at all recording whether the track was requested
    # via /vplay (video) or /play (audio-only). _play_next() and
    # try_autoplay() re-play tracks from the queue / AutoPlay without any
    # video argument, so they always defaulted to audio-only — meaning any
    # /vplay request that got queued (something else already playing) came
    # back as audio-only the moment it was actually dequeued and played.
    # Storing the intent on the Track itself makes it survive being queued,
    # popped, looped, or replayed by AutoPlay.
    video: bool = False


# In-memory per-chat state
_queues: dict[int, list[Track]] = {}
_current: dict[int, Track] = {}
_loop: dict[int, str] = {}       # "none" | "single" | "all"
_volume: dict[int, int] = {}     # 0-200 (0 = muted)
_predownloaded: dict[int, Track] = {}  # chat_id -> next AutoPlay track, already cached to /tmp


def get_queue(chat_id: int) -> list[Track]:
    return _queues.get(chat_id, [])


def add_to_queue(chat_id: int, track: Track):
    if chat_id not in _queues:
        _queues[chat_id] = []
    _queues[chat_id].append(track)


def pop_next(chat_id: int) -> Optional[Track]:
    """Pop next track from queue. Handles loop modes."""
    mode = _loop.get(chat_id, "none")
    current = _current.get(chat_id)

    if mode == "single" and current:
        return current

    if _queues.get(chat_id):
        track = _queues[chat_id].pop(0)
        if mode == "all" and current:
            _queues[chat_id].append(current)
        _current[chat_id] = track
        return track

    return None


def set_current(chat_id: int, track: Track):
    _current[chat_id] = track


def get_current(chat_id: int) -> Optional[Track]:
    return _current.get(chat_id)


def clear_queue(chat_id: int):
    _queues[chat_id] = []
    _current.pop(chat_id, None)


def remove_from_queue(chat_id: int, position: int) -> Optional[Track]:
    """Remove track at 1-based position."""
    q = _queues.get(chat_id, [])
    idx = position - 1
    if 0 <= idx < len(q):
        return q.pop(idx)
    return None


def shuffle_queue(chat_id: int):
    q = _queues.get(chat_id, [])
    random.shuffle(q)
    _queues[chat_id] = q


# ─── Loop ────────────────────────────────────────────────────────────────────

def set_loop(chat_id: int, mode: str):
    """mode: 'none' | 'single' | 'all'"""
    _loop[chat_id] = mode


def get_loop(chat_id: int) -> str:
    return _loop.get(chat_id, "none")


# ─── Volume ──────────────────────────────────────────────────────────────────

def get_volume(chat_id: int) -> int:
    return _volume.get(chat_id, 100)


def set_volume_local(chat_id: int, vol: int):
    # Allow 0 (mute) up to 200
    _volume[chat_id] = max(0, min(200, vol))


# ─── AutoPlay pre-download cache ──────────────────────────────────────────────
# Holds the NEXT track AutoPlay has already predicted + downloaded for this
# chat, so when the current song ends there is zero download wait.

def set_predownloaded(chat_id: int, track: Optional[Track]):
    if track is None:
        _predownloaded.pop(chat_id, None)
    else:
        _predownloaded[chat_id] = track


def pop_predownloaded(chat_id: int) -> Optional[Track]:
    return _predownloaded.pop(chat_id, None)


def peek_predownloaded(chat_id: int) -> Optional[Track]:
    return _predownloaded.get(chat_id)


# ─── Autoplay (persisted in DB) ───────────────────────────────────────────────

async def is_autoplay_on(chat_id: int) -> bool:
    val = await get_setting(chat_id, "autoplay", True)
    return bool(val)


async def set_autoplay(chat_id: int, enabled: bool):
    await set_setting(chat_id, "autoplay", enabled)


# ─── Queue display (HTML) ─────────────────────────────────────────────────────

def format_queue(chat_id: int, autoplay_on: bool = False) -> str:
    """
    Returns an HTML-formatted queue string, wrapped in a native Telegram
    <blockquote> so /queue always renders as a quote card.
    Song titles / requester names are html.escape()'d so characters like
    & < > ' " never break Telegram's HTML entity parser.

    BUG FIX ("autoplay on kiya but queue is empty dikha raha"): when the
    manual queue is empty AND no predownloaded track exists yet, this used
    to unconditionally print "Queue is empty" — even when AutoPlay was ON
    and a related track was being predicted/downloaded in the background.
    That misleading message made users think AutoPlay was broken. Now:
    when AutoPlay is ON, show "🤖 AutoPlay is ON — next song will be picked
    automatically" instead of the dead-end "Queue is empty" text.
    """
    current = _current.get(chat_id)
    q = _queues.get(chat_id, [])
    predownloaded = _predownloaded.get(chat_id)

    lines = [f"<b>{premium_emoji(PREMIUM_EMOJI_IDS['queue'], '📋')} Music Queue</b>\n"]
    if current:
        safe_title = html.escape(current.title[:45])
        safe_name  = html.escape(current.requester_name)
        lines.append(f"<b>▶️ Now Playing:</b>\n<code>{safe_title}</code> — {safe_name}\n")

    if q:
        lines.append("<b>⏳ Up Next:</b>")
        for i, t in enumerate(q[:10], 1):
            safe_t = html.escape(t.title[:40])
            safe_n = html.escape(t.requester_name)
            lines.append(f"<code>{i}.</code> {safe_t} — <i>{safe_n}</i>")
        if len(q) > 10:
            lines.append(f"\n<i>...and {len(q) - 10} more</i>")
        if predownloaded:
            safe_p = html.escape(predownloaded.title[:40])
            lines.append(f"\n<b>🤖 AutoPlay ready:</b> <code>{safe_p}</code> (pre-downloaded)")
    elif predownloaded:
        safe_p = html.escape(predownloaded.title[:40])
        lines.append("<b>⏳ Up Next (AutoPlay):</b>")
        lines.append(f"<code>{safe_p}</code>")
        lines.append("🙋 Requested by: <i>AutoPlay</i>")
    elif autoplay_on:
        lines.append("🤖 <b>AutoPlay is ON</b> — next song will be picked automatically")
    else:
        lines.append("<i>Queue is empty</i>")

    return f"<blockquote>{chr(10).join(lines)}</blockquote>"
