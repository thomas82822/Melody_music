"""
📞 Voice call management — pytgcalls 3.0.0.dev / GroupCallFactory API
"""
import asyncio
import os
import glob
from pytgcalls import GroupCallFactory
from melody.logging import LOGGER, send_error_log
from melody.core.queue import (
    get_current, set_current, pop_next, clear_queue,
    get_volume, set_volume_local, is_autoplay_on,
)
from melody import assistant

# One factory per bot session
_factory = GroupCallFactory(assistant)

# Per-chat active GroupCallFile instances and play state
_calls: dict = {}       # chat_id -> GroupCallFile
_active: dict = {}      # chat_id -> bool


async def start_call_py():
    """GroupCallFactory needs no global start — calls are created per-chat."""
    LOGGER.info("PyTgCalls (GroupCallFactory) ready.")


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _make_call(chat_id: int):
    """Create a new GroupCallFile for a chat and register its end-handler."""
    call = _factory.get_file_group_call(input_filename=None, play_on_repeat=False)

    @call.on_playout_ended
    async def _on_ended(gc, filename):
        # Delete the finished audio file to save /tmp space
        if filename:
            try:
                os.unlink(filename)
            except Exception:
                pass
        await _play_next(chat_id)

    return call


async def _play_next(chat_id: int):
    """Advance queue or handle autoplay/stop."""
    from melody.core.autoplay import try_autoplay

    next_track = pop_next(chat_id)
    if next_track:
        await _stream_track(chat_id, next_track)
    else:
        _active.pop(chat_id, None)
        call = _calls.pop(chat_id, None)
        if call:
            try:
                await call.stop()
            except Exception:
                pass
        if await is_autoplay_on(chat_id):
            await try_autoplay(chat_id)


async def _stream_track(chat_id: int, track, video: bool = False):
    """Download and play a track. Reuses existing call if already in voice chat."""
    try:
        from melody.core.ytdl import download_audio
        filepath = await download_audio(track.video_id)

        if _active.get(chat_id):
            # Already in voice chat — change the file (triggers restart_playout)
            _calls[chat_id].input_filename = filepath
        else:
            call = _make_call(chat_id)
            _calls[chat_id] = call
            call.input_filename = filepath
            await call.start(chat_id)
            _active[chat_id] = True

            # Apply stored volume
            vol = get_volume(chat_id)
            if vol != 100:
                try:
                    await call.set_my_volume(vol)
                except Exception:
                    pass

    except Exception as exc:
        _active.pop(chat_id, None)
        _calls.pop(chat_id, None)
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
    call = _calls.get(chat_id)
    if call:
        try:
            call.pause_playout()
        except Exception as exc:
            await send_error_log(f"pause_stream failed in {chat_id}", exc)


async def resume_stream(chat_id: int):
    call = _calls.get(chat_id)
    if call:
        try:
            call.resume_playout()
        except Exception as exc:
            await send_error_log(f"resume_stream failed in {chat_id}", exc)


async def skip_stream(chat_id: int):
    """Skip current track and play next."""
    await _play_next(chat_id)


async def stop_stream(chat_id: int):
    """Stop playback, clear queue, and leave voice chat."""
    try:
        clear_queue(chat_id)
        _active.pop(chat_id, None)
        call = _calls.pop(chat_id, None)
        if call:
            await call.stop()
    except Exception as exc:
        await send_error_log(f"stop_stream failed in {chat_id}", exc)


async def change_volume(chat_id: int, volume: int):
    """Set volume (0 = mute, 1-200 = normal range)."""
    volume = max(0, min(200, volume))
    set_volume_local(chat_id, volume)
    call = _calls.get(chat_id)
    if call:
        try:
            if volume == 0:
                await call.set_is_mute(True)
            else:
                await call.set_is_mute(False)
                await call.set_my_volume(volume)
        except Exception as exc:
            await send_error_log(f"change_volume failed in {chat_id}", exc)


async def seek_stream(chat_id: int, seconds: int):
    """Seek is not supported in GroupCallFile API — silently no-op."""
    LOGGER.warning("seek_stream: not supported in pytgcalls 3.0.0.dev (file API), seconds=%d", seconds)


async def is_active(chat_id: int) -> bool:
    return _active.get(chat_id, False)
