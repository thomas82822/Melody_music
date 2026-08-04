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

def format_queue(chat_id: int) -> str:
    """
    Returns an HTML-formatted queue string safe for parse_mode=HTML.
    Song titles / requester names are html.escape()'d so characters like
    & < > ' " never break Telegram's HTML entity parser.
    """
    current = _current.get(chat_id)
    q = _queues.get(chat_id, [])

    lines = ["<b>📋 Music Queue</b>\n"]
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
    else:
        lines.append("<i>Queue is empty</i>")

    return "\n".join(lines)
