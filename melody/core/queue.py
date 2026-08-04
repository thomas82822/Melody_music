"""
📋 Queue management — per-chat in-memory queues with settings
"""
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


# ─── Queue display ────────────────────────────────────────────────────────────

def format_queue(chat_id: int) -> str:
    current = _current.get(chat_id)
    q = _queues.get(chat_id, [])

    lines = ["**📋 Music Queue**\n"]
    if current:
        lines.append(f"**▶️ Now Playing:**\n`{current.title[:45]}` — {current.requester_name}\n")

    if q:
        lines.append("**⏳ Up Next:**")
        for i, t in enumerate(q[:10], 1):
            lines.append(f"`{i}.` {t.title[:40]} — _{t.requester_name}_")
        if len(q) > 10:
            lines.append(f"\n_...and {len(q) - 10} more_")
    else:
        lines.append("_Queue is empty_")

    return "\n".join(lines)
