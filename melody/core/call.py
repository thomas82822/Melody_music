"""
📞 Voice call management — py-tgcalls 2.x (PyTgCalls + MediaStream API)
"""
import glob
import os
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioQuality, MediaStream, StreamEnded
from melody.logging import LOGGER, send_error_log
from melody.core.queue import (
    get_current, set_current, pop_next, clear_queue,
    get_volume, set_volume_local, is_autoplay_on,
)
from melody import assistant

# One PyTgCalls instance per assistant client
_pytgcalls = PyTgCalls(assistant)

# Per-chat play state
_active: dict = {}   # chat_id -> bool


async def start_call_py():
    """Start the PyTgCalls service. Must be called once on bot startup."""
    await _pytgcalls.start()
    LOGGER.info("PyTgCalls (py-tgcalls 2.x) started.")


# ─── Stream-end event ─────────────────────────────────────────────────────────
# FIX: py-tgcalls 2.x removed on_stream_end() — use on_update() and filter
# by isinstance(update, StreamEnded) instead.

@_pytgcalls.on_update()
async def _on_stream_end(_, update):
    if not isinstance(update, StreamEnded):
        return
    chat_id = getattr(update, "chat_id", None)
    if chat_id is None:
        return
    # Delete finished audio file to save disk space
    current = get_current(chat_id)
    if current:
        for f in glob.glob(f"/tmp/melody_{current.video_id}.*"):
            try:
                os.unlink(f)
            except Exception:
                pass
    await _play_next(chat_id)


# ─── Internal helpers ─────────────────────────────────────────────────────────

async def _play_next(chat_id: int):
    """Advance queue or handle autoplay / stop."""
    from melody.core.autoplay import try_autoplay

    next_track = pop_next(chat_id)
    if next_track:
        await _stream_track(chat_id, next_track)
    else:
        _active.pop(chat_id, None)
        try:
            await _pytgcalls.leave_group_call(chat_id)
        except Exception:
            pass
        if await is_autoplay_on(chat_id):
            await try_autoplay(chat_id)


async def _stream_track(chat_id: int, track, video: bool = False):
    """Download and play a track. Reuses existing call if already in voice chat."""
    try:
        from melody.core.ytdl import download_audio
        filepath = await download_audio(track.video_id)

        stream = MediaStream(filepath, audio_parameters=AudioQuality.STUDIO)

        if _active.get(chat_id):
            await _pytgcalls.change_stream(chat_id, stream)
        else:
            await _pytgcalls.join_group_call(chat_id, stream)
            _active[chat_id] = True

            # Apply stored volume
            vol = get_volume(chat_id)
            if vol != 100:
                try:
                    await _pytgcalls.change_volume_call(chat_id, vol)
                except Exception:
                    pass

    except Exception as exc:
        _active.pop(chat_id, None)
        await send_error_log(f"_stream_track failed in {chat_id}", exc)


# ─── Public API ───────────────────────────────────────────────────────────────

async def play_stream(chat_id: int, track, video: bool = False) -> bool:
    """Start or queue a track. Returns True if playing now, False if queued."""
    from melody.core.queue import add_to_queue

    if _active.get(chat_id):
        add_to_queue(chat_id, track)
        return False  # queued

    set_current(chat_id, track)
    await _stream_track(chat_id, track, video=video)
    return True  # playing now


async def pause_stream(chat_id: int):
    try:
        await _pytgcalls.pause_stream(chat_id)
    except Exception as exc:
        await send_error_log(f"pause_stream failed in {chat_id}", exc)


async def resume_stream(chat_id: int):
    try:
        await _pytgcalls.resume_stream(chat_id)
    except Exception as exc:
        await send_error_log(f"resume_stream failed in {chat_id}", exc)


async def skip_stream(chat_id: int):
    await _play_next(chat_id)


async def stop_stream(chat_id: int):
    """Stop playback, clear queue, and leave voice chat."""
    try:
        clear_queue(chat_id)
        _active.pop(chat_id, None)
        await _pytgcalls.leave_group_call(chat_id)
    except Exception as exc:
        await send_error_log(f"stop_stream failed in {chat_id}", exc)


async def change_volume(chat_id: int, volume: int):
    """Set volume (0-200)."""
    volume = max(0, min(200, volume))
    set_volume_local(chat_id, volume)
    try:
        if volume == 0:
            await _pytgcalls.mute_stream(chat_id)
        else:
            await _pytgcalls.unmute_stream(chat_id)
            await _pytgcalls.change_volume_call(chat_id, volume)
    except Exception as exc:
        await send_error_log(f"change_volume failed in {chat_id}", exc)


async def seek_stream(chat_id: int, seconds: int):
    """Seek is not supported in pytgcalls file streaming — no-op."""
    LOGGER.warning("seek_stream: not supported in py-tgcalls file mode, seconds=%d", seconds)


async def is_active(chat_id: int) -> bool:
    return _active.get(chat_id, False)
