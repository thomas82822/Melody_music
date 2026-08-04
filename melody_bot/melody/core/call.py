"""
📞 Voice call management — py-tgcalls 2.x (PyTgCalls + MediaStream API)

FIX 1 (Silent crash): _pytgcalls was created at module level using
    `from melody import assistant`, which triggered melody/__init__.py
    (client creation) at import time — before validate_config() ran.
    Moved to lazy init inside start_call_py().

FIX 2 (AttributeError crash): AudioQuality.STUDIO does not exist in
    py-tgcalls >= 2.0. Replaced with HIGH_QUALITY (2.x constant name),
    with a safe fallback in case the installed version differs.

FIX 3: @_pytgcalls.on_update() decorator registration moved inside
    start_call_py() because the instance doesn't exist at import time.
"""
import glob
import os
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, StreamEnded
from melody.logging import LOGGER, send_error_log
from melody.core.queue import (
    get_current, set_current, pop_next, clear_queue,
    get_volume, set_volume_local, is_autoplay_on,
)

# Lazy — set by start_call_py() on first call
_pytgcalls: "PyTgCalls | None" = None

# Per-chat play state
_active: dict = {}   # chat_id -> bool


def _get_audio_quality():
    """Return best available AudioQuality constant for py-tgcalls 2.x."""
    from pytgcalls.types import AudioQuality
    # py-tgcalls 2.x uses HIGH_QUALITY; older 1.x had STUDIO — try both.
    return getattr(AudioQuality, "HIGH_QUALITY", None) or getattr(AudioQuality, "STUDIO", None)


async def start_call_py():
    """
    Initialise PyTgCalls and register the stream-end handler.
    Called once from __main__.py AFTER assistant.start().
    """
    global _pytgcalls

    from melody import assistant  # safe: create_clients() already ran
    _pytgcalls = PyTgCalls(assistant)

    @_pytgcalls.on_update()
    async def _on_stream_end(_, update):
        if not isinstance(update, StreamEnded):
            return
        chat_id = getattr(update, "chat_id", None)
        if chat_id is None:
            return
        current = get_current(chat_id)
        if current:
            for f in glob.glob(f"/tmp/melody_{current.video_id}.*"):
                try:
                    os.unlink(f)
                except Exception:
                    pass
        await _play_next(chat_id)

    await _pytgcalls.start()
    LOGGER.info("PyTgCalls (py-tgcalls 2.x) started.")


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

        audio_quality = _get_audio_quality()
        stream = MediaStream(filepath, audio_parameters=audio_quality)

        if _active.get(chat_id):
            await _pytgcalls.change_stream(chat_id, stream)
        else:
            await _pytgcalls.join_group_call(chat_id, stream)
            _active[chat_id] = True

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
        return False

    set_current(chat_id, track)
    await _stream_track(chat_id, track, video=video)
    return True


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
    """Stop playback, clear queue, leave voice chat."""
    clear_queue(chat_id)
    _active.pop(chat_id, None)
    try:
        await _pytgcalls.leave_group_call(chat_id)
    except Exception:
        pass


async def seek_stream(chat_id: int, seconds: int):
    try:
        await _pytgcalls.seek_stream(chat_id, seconds)
    except Exception as exc:
        await send_error_log(f"seek_stream failed in {chat_id}", exc)


async def change_volume(chat_id: int, volume: int):
    set_volume_local(chat_id, volume)
    try:
        await _pytgcalls.change_volume_call(chat_id, volume)
    except Exception as exc:
        await send_error_log(f"change_volume failed in {chat_id}", exc)


def is_active(chat_id: int) -> bool:
    return bool(_active.get(chat_id))


async def get_participants(chat_id: int) -> list:
    try:
        return await _pytgcalls.get_participants(chat_id)
    except Exception:
        return []
