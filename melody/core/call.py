"""
📞 Voice call management — py-tgcalls 2.x (PyTgCalls + MediaStream API)

FIXES APPLIED:
  • Instant VC join (silence trick) — bot joins the voice chat IMMEDIATELY
    with a short silence stream before yt-dlp finishes searching/downloading.
    When the real audio is ready, change_stream() swaps in the song (~instant).
    User hears the bot join in <1 s instead of waiting 5-8 s for yt-dlp.

  • Silence race guard — _silence_playing[chat_id] flag prevents the silence
    file's stream_end event from being treated as "song finished". Without this,
    the bot would leave VC prematurely if the silence ends before the song
    download completes.

  • Pipe-safe cleanup — /tmp files from FIFO pipe paths are NOT cleaned up
    (the FIFO writer thread handles its own tmpdir). Only real /tmp/melody_*
    files are deleted after playback to free space on Heroku's 512 MB /tmp.

FIX 1 (Silent crash): lazy PyTgCalls init inside start_call_py().
FIX 2 (AttributeError): AudioQuality.HIGH_QUALITY (2.x) with STUDIO fallback.
FIX 3: Handler registration moved inside start_call_py().
"""
import asyncio
import glob
import os
import tempfile
import time

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
_active: dict = {}             # chat_id → bool
_silence_playing: dict = {}    # chat_id → bool; True while silence stream is active


# ─── Audio quality helper ─────────────────────────────────────────────────────

def _get_audio_quality():
    """Return best available AudioQuality constant for py-tgcalls 2.x."""
    from pytgcalls.types import AudioQuality
    return getattr(AudioQuality, "HIGH_QUALITY", None) or getattr(AudioQuality, "STUDIO", None)


# ─── Silence file (instant VC join) ──────────────────────────────────────────

_SILENCE_PATH: str | None = None
_SILENCE_LOCK = asyncio.Lock()


async def _get_silence_file() -> str | None:
    """
    Create once: a 4-second PCM silence MP3.
    Used to join VC instantly before yt-dlp finishes downloading.
    """
    global _SILENCE_PATH
    if _SILENCE_PATH and os.path.exists(_SILENCE_PATH):
        return _SILENCE_PATH
    async with _SILENCE_LOCK:
        if _SILENCE_PATH and os.path.exists(_SILENCE_PATH):
            return _SILENCE_PATH
        path = os.path.join(tempfile.gettempdir(), "melody_vc_silence.mp3")
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-t", "4",
                "-c:a", "libmp3lame", "-b:a", "64k",
                path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=15)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                _SILENCE_PATH = path
                LOGGER.info("✅ Silence file created: %s", path)
        except Exception as e:
            LOGGER.debug("Silence file creation failed: %s", e)
    return _SILENCE_PATH


# ─── Startup ─────────────────────────────────────────────────────────────────

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

        # Silence race guard: if the silence stream ends before the real song
        # is ready, do NOT advance the queue — let _stream_track handle it.
        if _silence_playing.get(chat_id):
            LOGGER.debug("stream_end during silence for %d — ignoring (real song loading)", chat_id)
            return

        # Clean up the finished track's /tmp file (skip FIFO paths)
        current = get_current(chat_id)
        if current:
            _cleanup_track_file(current.video_id)

        await _play_next(chat_id)

    await _pytgcalls.start()
    LOGGER.info("PyTgCalls (py-tgcalls 2.x) started.")

    # Pre-generate the silence file so first /play is instant
    asyncio.create_task(_get_silence_file())


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _cleanup_track_file(video_id: str):
    """Delete /tmp/melody_<video_id>.* after playback.
    Skips FIFO pipe paths (they clean themselves up in the writer thread).
    """
    for f in glob.glob(f"/tmp/melody_{video_id}.*"):
        try:
            os.unlink(f)
        except Exception:
            pass


async def _play_next(chat_id: int):
    """Advance queue or handle autoplay / stop."""
    from melody.core.autoplay import try_autoplay

    next_track = pop_next(chat_id)
    if next_track:
        await _stream_track(chat_id, next_track)
    else:
        _active.pop(chat_id, None)
        _silence_playing.pop(chat_id, None)
        try:
            await _pytgcalls.leave_group_call(chat_id)
        except Exception:
            pass
        if await is_autoplay_on(chat_id):
            await try_autoplay(chat_id)


async def _stream_track(chat_id: int, track, video: bool = False):
    """
    Download (or pipe-stream) a track and start/swap into the active VC.

    If the bot joined VC early with silence (_active[chat_id] is already True),
    this calls change_stream() which is near-instant — the user hears music
    within ~100 ms of the download path returning.
    """
    try:
        from melody.core.ytdl import download_audio
        filepath = await download_audio(track.video_id, audio_only=not video)

        audio_quality = _get_audio_quality()
        stream = MediaStream(filepath, audio_parameters=audio_quality)

        # Clear silence flag before change_stream so any stream_end events
        # from now on are treated as the real song finishing.
        _silence_playing.pop(chat_id, None)

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
        _silence_playing.pop(chat_id, None)
        await send_error_log(f"_stream_track failed in {chat_id}", exc)


# ─── Public API ───────────────────────────────────────────────────────────────

async def play_stream(chat_id: int, track, video: bool = False) -> bool:
    """
    Start or queue a track.
    Returns True if playing now, False if queued.

    ⚡ INSTANT VC JOIN:
    If the bot is not yet in VC, we join immediately with a short silence
    stream so the user sees the bot appear in the call right away.  The real
    song download runs concurrently; when it finishes, change_stream() swaps
    in the audio (~instant swap vs. slow initial join).
    """
    from melody.core.queue import add_to_queue

    if _active.get(chat_id):
        add_to_queue(chat_id, track)
        return False

    set_current(chat_id, track)

    # ⚡ Step 1: Join VC immediately with silence (non-blocking)
    silence = await _get_silence_file()
    if silence and _pytgcalls:
        try:
            audio_quality = _get_audio_quality()
            sstream = MediaStream(silence, audio_parameters=audio_quality)
            _silence_playing[chat_id] = True
            await asyncio.wait_for(
                _pytgcalls.join_group_call(chat_id, sstream),
                timeout=8.0,
            )
            _active[chat_id] = True
            LOGGER.debug("⚡ Instant VC join done for %d", chat_id)
        except asyncio.TimeoutError:
            LOGGER.debug("Instant VC join timed out for %d — will join with real song", chat_id)
            _silence_playing.pop(chat_id, None)
        except Exception as e:
            LOGGER.debug("Instant VC join failed for %d: %s — will join with real song", chat_id, e)
            _silence_playing.pop(chat_id, None)

    # ⚡ Step 2: Download / pipe-stream the real song concurrently
    # If silence join succeeded, change_stream swaps in audio when ready.
    # If silence join failed, _stream_track joins VC normally with the real song.
    asyncio.create_task(_stream_track(chat_id, track, video=video))
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
    _silence_playing.pop(chat_id, None)
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
