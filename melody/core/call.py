"""
📞 Voice call management — PyTgCalls 2.x wrapper
"""
import asyncio
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from pytgcalls.types.stream import StreamAudioEnded
from melody.logging import LOGGER, send_error_log
from melody.core.queue import (
    get_current, set_current, pop_next, clear_queue,
    get_volume, set_volume_local, is_autoplay_on,
)
from melody import assistant

call_py = PyTgCalls(assistant)

# Active chats
_active: dict[int, bool] = {}


async def start_call_py():
    """Start PyTgCalls listener."""
    await call_py.start()


# ─── Stream finished handler ──────────────────────────────────────────────────

@call_py.on_stream_end()
async def stream_end_handler(_, update):
    if isinstance(update, StreamAudioEnded):
        chat_id = update.chat_id
        await _play_next(chat_id)


async def _play_next(chat_id: int):
    """Play next track from queue, or handle autoplay."""
    from melody.core.autoplay import try_autoplay

    next_track = pop_next(chat_id)
    if next_track:
        await _stream_track(chat_id, next_track)
    else:
        _active.pop(chat_id, None)
        if await is_autoplay_on(chat_id):
            await try_autoplay(chat_id)


# ─── Public API ───────────────────────────────────────────────────────────────

async def play_stream(chat_id: int, track, video: bool = False):
    """Start or queue a track. Returns True if playing now, False if queued."""
    from melody.core.queue import add_to_queue

    if _active.get(chat_id):
        add_to_queue(chat_id, track)
        return False  # queued

    set_current(chat_id, track)
    await _stream_track(chat_id, track, video=video)
    return True  # playing now


async def _stream_track(chat_id: int, track, video: bool = False):
    try:
        stream = AudioPiped(track.stream_url)

        if _active.get(chat_id):
            await call_py.change_stream(chat_id, stream)
        else:
            await call_py.join_group_call(chat_id, stream)
            _active[chat_id] = True

        vol = get_volume(chat_id)
        await call_py.change_volume_call(chat_id, vol)

    except Exception as exc:
        _active.pop(chat_id, None)
        await send_error_log(f"_stream_track failed in {chat_id}", exc)


async def pause_stream(chat_id: int):
    try:
        await call_py.pause_stream(chat_id)
    except Exception as exc:
        await send_error_log(f"pause_stream failed in {chat_id}", exc)


async def resume_stream(chat_id: int):
    try:
        await call_py.resume_stream(chat_id)
    except Exception as exc:
        await send_error_log(f"resume_stream failed in {chat_id}", exc)


async def skip_stream(chat_id: int):
    await _play_next(chat_id)


async def stop_stream(chat_id: int):
    try:
        clear_queue(chat_id)
        _active.pop(chat_id, None)
        await call_py.leave_group_call(chat_id)
    except Exception as exc:
        await send_error_log(f"stop_stream failed in {chat_id}", exc)


async def change_volume(chat_id: int, volume: int):
    set_volume_local(chat_id, volume)
    try:
        await call_py.change_volume_call(chat_id, volume)
    except Exception as exc:
        await send_error_log(f"change_volume failed in {chat_id}", exc)


async def seek_stream(chat_id: int, seconds: int):
    try:
        await call_py.seek_stream(chat_id, seconds)
    except Exception as exc:
        await send_error_log(f"seek_stream failed in {chat_id}", exc)


async def is_active(chat_id: int) -> bool:
    return _active.get(chat_id, False)
