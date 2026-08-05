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

  • Per-chat play lock (FIX concurrent /play race) — if two users type /play
    at almost the same moment, both could previously pass the `_active` check
    before either had set _active[chat_id] = True, causing both to try to
    start a new stream instead of one playing and one queuing. _play_locks
    serialises play_stream() per chat: the second request always sees the
    correct _active state and is properly added to the queue.

FIX 1 (Silent crash): lazy PyTgCalls init inside start_call_py().
FIX 2 (AttributeError): AudioQuality.HIGH_QUALITY (2.x) with STUDIO fallback.
FIX 3: Handler registration moved inside start_call_py().
FIX 4: Per-chat asyncio locks eliminate the concurrent /play race condition.
"""
import asyncio
import glob
import os
import tempfile
import time

from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, StreamEnded
from pytgcalls.exceptions import NoActiveGroupCall
from pyrogram import enums
from pyrogram.types import ChatPermissions
from pyrogram.errors import ChannelInvalid, ChannelPrivate, PeerIdInvalid, UserBannedInChannel
from melody.logging import LOGGER, send_error_log
from melody.core.queue import (
    get_current, set_current, pop_next, clear_queue,
    get_volume, set_volume_local, is_autoplay_on, get_queue,
)

# Shown to the group whenever we try to (re)join / stream but Telegram
# reports there is no active voice/video chat at all (py-tgcalls raises
# NoActiveGroupCall — a video chat must already be started by someone in
# the app before the bot/assistant can join it).
NO_ACTIVE_VC_MESSAGE = (
    "ɴᴏ ᴀᴄᴛɪᴠᴇ ᴠɪᴅᴇᴏᴄʜᴀᴛ ꜰᴏᴜɴᴅ.\n\n"
    "ᴘʟᴇᴀsᴇ sᴛᴀʀᴛ ᴠɪᴅᴇᴏᴄʜᴀᴛ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ / ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ."
)

# Lazy — set by start_call_py() on first call
_pytgcalls: "PyTgCalls | None" = None

# Per-chat play state
_active: dict = {}             # chat_id → bool
_silence_playing: dict = {}    # chat_id → bool; True while silence stream is active
_is_video: dict = {}           # chat_id → bool; True if current track is streaming as video
_play_start_time: dict = {}    # chat_id → float (time.time()) when current track started/last sought
_seek_offset: dict = {}        # chat_id → int seconds; playback position baked into the last stream swap

# FIX 4: Per-chat locks that serialise play_stream() calls.
# Two concurrent /play commands for the same group acquire this lock in order;
# the second one always sees the updated _active state and gets queued instead
# of trying to start a second stream simultaneously.
_play_locks: dict[int, asyncio.Lock] = {}


def _get_play_lock(chat_id: int) -> asyncio.Lock:
    if chat_id not in _play_locks:
        _play_locks[chat_id] = asyncio.Lock()
    return _play_locks[chat_id]


# ─── Audio quality helper ─────────────────────────────────────────────────────

def _get_audio_quality():
    """Return best available AudioQuality constant for py-tgcalls 2.x."""
    from pytgcalls.types import AudioQuality
    return getattr(AudioQuality, "HIGH_QUALITY", None) or getattr(AudioQuality, "STUDIO", None)


def _get_video_quality():
    """Return the VideoQuality used for /vplay-style video streams."""
    from pytgcalls.types import VideoQuality
    return VideoQuality.HD_720p


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
    """Delete /tmp/melody_<video_id>_<a|v>.* after playback.
    Skips FIFO pipe paths (they clean themselves up in the writer thread).

    NOTE: matches both the "_a" (audio-only) and "_v" (video) cache variants
    — see ytdl.download_audio()'s audio/video cache-key fix — so leftover
    files from either variant are actually removed instead of silently
    surviving because the old glob (`melody_<id>.*`, no variant suffix)
    no longer matches the new filenames.
    """
    for f in glob.glob(f"/tmp/melody_{video_id}_*.*"):
        try:
            os.unlink(f)
        except Exception:
            pass


async def _play_next(chat_id: int):
    """
    Advance queue or handle autoplay / stop.

    BUG FIX ("autoplay on kiya phir bhi bot VC left kar diya"): this used to
    unconditionally leave the call FIRST and only THEN check AutoPlay —
    so even with AutoPlay on, the bot visibly dropped out of the voice chat
    before (maybe) trying to rejoin, and `try_autoplay()`'s own `is_active`
    guard (see autoplay.py) made that rejoin silently no-op most of the
    time. Now: if the manual queue is empty, try AutoPlay WHILE still
    connected — the bot never leaves the call at all when AutoPlay has a
    track to play. Only leave if there really is nothing left to play.
    """
    from melody.core.autoplay import try_autoplay

    next_track = pop_next(chat_id)
    if next_track:
        # BUG FIX ("kabhi vplay kabhi play"): this used to call _stream_track
        # with no `video` argument at all, so it always defaulted to False —
        # a queued /vplay track silently turned into audio-only the moment
        # it advanced from the queue. Track now carries its own video intent
        # (see queue.Track), so replay it exactly as it was requested.
        await _stream_track(chat_id, next_track, video=next_track.video)
        return

    if await is_autoplay_on(chat_id) and await try_autoplay(chat_id):
        return

    _active.pop(chat_id, None)
    _silence_playing.pop(chat_id, None)
    _is_video.pop(chat_id, None)
    _play_start_time.pop(chat_id, None)
    _seek_offset.pop(chat_id, None)
    try:
        await _pytgcalls.leave_call(chat_id)
    except Exception:
        pass


async def _stream_track(chat_id: int, track, video: bool = False, _retry: bool = False):
    """
    Download (or pipe-stream) a track and start/swap into the active VC.

    If the bot joined VC early with silence (_active[chat_id] is already True),
    this calls change_stream() which is near-instant — the user hears music
    within ~100 ms of the download path returning.

    `_retry` is internal-only: set when this call is a single automatic
    retry after `_auto_join_assistant()` successfully joined the assistant
    to the chat, so a second failure doesn't loop forever.
    """
    try:
        from melody.core.ytdl import download_audio
        filepath = await download_audio(track.video_id, audio_only=not video)

        audio_quality = _get_audio_quality()
        if video:
            # ROOT-CAUSE FIX (/vplay not showing video): MediaStream only
            # auto-detects the video track from `filepath` when it isn't
            # explicitly told to ignore it, but the call must be *joined*
            # with video capability negotiated from the start — see
            # pre_join()'s `video` flag, which skips the audio-only silence
            # join for video requests specifically so this first play() call
            # is the one that establishes the call and always carries video.
            stream = MediaStream(
                filepath,
                audio_parameters=audio_quality,
                video_parameters=_get_video_quality(),
            )
        else:
            stream = MediaStream(filepath, audio_parameters=audio_quality)

        # Clear silence flag before change_stream so any stream_end events
        # from now on are treated as the real song finishing.
        _silence_playing.pop(chat_id, None)

        # py-tgcalls 2.x has a single `play()` entrypoint: it joins the call
        # if not already active, or swaps the stream source in-place if the
        # chat is already in a call. There is no separate join_group_call()/
        # change_stream() pair like older 1.x releases.
        was_active = _active.get(chat_id)
        await _pytgcalls.play(chat_id, stream)
        _active[chat_id] = True
        _is_video[chat_id] = video
        _play_start_time[chat_id] = time.time()
        _seek_offset[chat_id] = 0

        if not was_active:
            vol = get_volume(chat_id)
            if vol != 100:
                try:
                    await _pytgcalls.change_volume_call(chat_id, vol)
                except Exception:
                    pass

        # ⚡ AutoPlay pre-download: this song is now live. If nothing is
        # manually queued after it and AutoPlay is ON for this chat, predict
        # + download the next track RIGHT NOW in the background so there is
        # zero download wait once this one ends (see autoplay.prefetch_next).
        if not get_queue(chat_id) and await is_autoplay_on(chat_id):
            from melody.core.autoplay import prefetch_next
            asyncio.create_task(prefetch_next(chat_id))

    except Exception as exc:
        _active.pop(chat_id, None)
        _silence_playing.pop(chat_id, None)

        # ROOT-CAUSE FIX (⚠️ Melody Error Log: ChannelInvalid / PeerIdInvalid
        # / ChannelPrivate — "_stream_track failed"): joining a Telegram
        # group/voice-chat call happens over the ASSISTANT (userbot) account,
        # not the bot account. MTProto requires the calling account to
        # actually be a member of that chat to resolve its peer at all — if
        # the assistant was never added to the group (or was removed from
        # it), Telegram rejects the join with CHANNEL_INVALID/PEER_ID_INVALID
        # every single time, and no amount of retrying fixes it.
        #
        # AUTO-FIX (no more manual "add the assistant" step): the BOT account
        # is already in the group (that's how it received /play at all) and
        # is normally group-admin (needed for other commands), so it can
        # export/reuse an invite link and have the ASSISTANT join through it
        # automatically — no human action required. Only if that auto-join
        # itself fails (bot lacks invite permission, assistant banned, etc.)
        # do we fall back to telling the group to add the assistant manually.
        # FEATURE: no active voice/video chat in the group at all — this is
        # an expected user-side condition (nobody started the VC yet), not a
        # bug, so show the clear instructional message instead of the
        # generic failure text and skip the error-log spam.
        if isinstance(exc, NoActiveGroupCall):
            await _notify_playback_failed(chat_id, NO_ACTIVE_VC_MESSAGE)
            return

        # ROOT-CAUSE FIX (⚠️ Melody Error Log: ChannelInvalid / PeerIdInvalid
        # / ChannelPrivate — "_stream_track failed"): joining a Telegram
        # group/voice-chat call happens over the ASSISTANT (userbot) account,
        # not the bot account. MTProto requires the calling account to
        # actually be a member of that chat to resolve its peer at all — if
        # the assistant was never added to the group (or was removed from
        # it), Telegram rejects the join with CHANNEL_INVALID/PEER_ID_INVALID
        # every single time, and no amount of retrying fixes it.
        #
        # FEATURE (auto-unban/unmute): UserBannedInChannel means the
        # assistant WAS a member but got banned or muted — handled the same
        # way, since _auto_join_assistant() now lifts a ban/mute with the
        # bot's own admin rights before attempting the invite-link rejoin.
        #
        # AUTO-FIX (no more manual "add the assistant" step): the BOT account
        # is already in the group (that's how it received /play at all) and
        # is normally group-admin (needed for other commands), so it can
        # export/reuse an invite link and have the ASSISTANT join through it
        # automatically — no human action required. Only if that auto-join
        # itself fails (bot lacks invite permission, assistant banned, etc.)
        # do we fall back to telling the group to add the assistant manually.
        if isinstance(exc, (ChannelInvalid, ChannelPrivate, PeerIdInvalid, UserBannedInChannel)) and not _retry:
            LOGGER.warning("Assistant cannot resolve chat %s (%s) — attempting auto-join/unban.",
                            chat_id, type(exc).__name__)
            joined = await _auto_join_assistant(chat_id)
            if joined:
                LOGGER.info("✅ Assistant auto-joined/unbanned in chat %s — retrying playback.", chat_id)
                await _stream_track(chat_id, track, video=video, _retry=True)
                return
            await _notify_playback_failed(
                chat_id,
                "⚠️ <b>Melody ka voice-assistant account is group mein nahi hai, aur auto-join bhi fail ho gaya.</b>\n\n"
                "Voice chat me gaana bajane ke liye assistant account ka bhi is group ka "
                "member hona zaroori hai. Please assistant ko group mein manually add karo "
                "(ya bot ko 'Invite Users via Link' admin permission do) aur phir se "
                "<code>/play</code> try karo.",
            )
        elif isinstance(exc, (ChannelInvalid, ChannelPrivate, PeerIdInvalid, UserBannedInChannel)):
            # Already retried once after auto-join/unban and it still failed.
            await _notify_playback_failed(
                chat_id,
                "⚠️ <b>Assistant ko group mein add/unban karne ke baad bhi gaana play nahi ho paya.</b>\n\n"
                "Dobara <code>/play</code> try karo.",
            )
        else:
            await _notify_playback_failed(
                chat_id,
                "❌ <b>Gaana play nahi ho paya.</b>\n\nDobara <code>/play</code> try karo.",
            )

        await send_error_log(f"_stream_track failed in {chat_id}", exc)


# Cached assistant user id — resolved once via get_me(), reused everywhere
# below instead of hitting Telegram on every auto-join check.
_assistant_id: "int | None" = None


async def _get_assistant_id() -> "int | None":
    global _assistant_id
    if _assistant_id is not None:
        return _assistant_id
    try:
        from melody import assistant
        me = await assistant.get_me()
        _assistant_id = me.id
        return _assistant_id
    except Exception as exc:
        LOGGER.warning("Could not resolve assistant's own user id: %s", exc)
        return None


async def _unban_or_unmute_assistant(chat_id: int) -> None:
    """FEATURE: if the assistant account is banned or muted (restricted) in
    `chat_id`, lift that with the BOT's own admin rights before attempting
    to (re)join — no group admin has to do this by hand.

    Safe / best-effort: if the bot itself lacks ban/restrict rights, or the
    assistant was never a member at all (get_chat_member 404s), this just
    logs and falls through so the normal invite-link join below still runs.
    """
    try:
        from melody import bot
    except Exception:
        return

    assistant_id = await _get_assistant_id()
    if not assistant_id:
        return

    try:
        member = await bot.get_chat_member(chat_id, assistant_id)
    except Exception:
        # Not a member yet at all (or never was) — nothing to unban/unmute.
        return

    try:
        if member.status == enums.ChatMemberStatus.BANNED:
            LOGGER.warning("Assistant is banned in %s — auto-unbanning with bot's admin rights.", chat_id)
            await bot.unban_chat_member(chat_id, assistant_id)
        elif member.status == enums.ChatMemberStatus.RESTRICTED:
            perms = member.permissions
            is_muted = not (perms and perms.can_send_messages)
            if is_muted:
                LOGGER.warning("Assistant is muted/restricted in %s — auto-lifting restriction.", chat_id)
                await bot.restrict_chat_member(
                    chat_id, assistant_id, permissions=ChatPermissions(all_perms=True),
                )
    except Exception as exc:
        # Bot may not actually have ban/restrict rights in this chat — that's
        # a real limitation, not a bug, so just log and let the join attempt
        # below proceed (and fail with its own clear message if it must).
        LOGGER.warning("Could not auto-unban/unmute assistant in %s: %s", chat_id, exc)


async def _auto_join_assistant(chat_id: int) -> bool:
    """Make the assistant (userbot) account join `chat_id` automatically via
    an invite link exported by the bot account, so a group admin never has
    to manually add the assistant for voice chat playback to work.

    Also auto-fixes the far more common cause of the assistant "not being
    in the group": it WAS a member but got banned or muted at some point
    (e.g. an over-eager anti-raid bot, or a leftover restriction from
    before Melody was even added) — see _unban_or_unmute_assistant().

    Requires the BOT to already be a member with "invite users via link"
    permission (true for any group where /play works at all, since that's
    the standard admin permission set music bots ask for). Returns True only
    if the assistant is confirmedly a member afterwards.
    """
    try:
        from melody import bot, assistant
    except Exception as exc:
        LOGGER.warning("Auto-join: could not import bot/assistant clients: %s", exc)
        return False

    await _unban_or_unmute_assistant(chat_id)

    try:
        link = await bot.export_chat_invite_link(chat_id)
    except Exception as exc:
        LOGGER.warning("Auto-join: bot could not export invite link for %s: %s", chat_id, exc)
        return False

    try:
        await assistant.join_chat(link)
    except Exception as exc:
        # "USER_ALREADY_PARTICIPANT" etc. — assistant may already be in the
        # chat but pyrogram's local peer cache just doesn't know about it
        # yet (e.g. added by someone else after the assistant last started).
        # Either way, fall through to the get_chat() re-check below instead
        # of giving up immediately.
        LOGGER.debug("Auto-join: assistant.join_chat raised (may be harmless): %s", exc)

    try:
        await assistant.get_chat(chat_id)
        return True
    except Exception as exc:
        LOGGER.warning("Auto-join: assistant still cannot resolve %s after join attempt: %s", chat_id, exc)
        return False


async def _notify_playback_failed(chat_id: int, text: str):
    """Best-effort user-facing failure notice — never raises, never blocks.
    _stream_track() runs fire-and-forget (see play_stream()'s docstring), so
    without this a failed download/join was previously invisible to the
    group: play.py already shows "Now Playing" optimistically before this
    background task even resolves.
    """
    try:
        from melody import bot
        from pyrogram import enums
        await bot.send_message(chat_id, text, parse_mode=enums.ParseMode.HTML)
    except Exception:
        pass


# ─── Public API ───────────────────────────────────────────────────────────────

async def pre_join(chat_id: int, video: bool = False) -> bool:
    """
    ⚡ Requirement #4 — join the voice chat with silence THE INSTANT the
    command arrives, before we even know which track we're looking for.

    Call this from the command handler in parallel with (not after) the
    yt-dlp search, e.g.:

        asyncio.create_task(pre_join(chat.id))
        info = await get_video_info(query)   # runs concurrently

    Previously the VC join only happened inside play_stream(), which itself
    only ran AFTER get_video_info() resolved — meaning the multi-second
    search always happened before the bot ever appeared in the call. Calling
    pre_join() up front removes the search from the critical path entirely:
    the bot joins in the time it takes one Telegram RPC round-trip, and the
    real song swaps in via change_stream the moment yt-dlp resolves it.

    Idempotent / safe to call even if the chat is already active (either
    mid silence-join or already playing a real track) — no-ops in that case.

    ROOT-CAUSE FIX (/vplay video never showing): this silence trick always
    joined with an AUDIO-ONLY file (no camera track). Telegram/py-tgcalls
    negotiate whether a participant is broadcasting video at *join* time —
    swapping in a video MediaStream afterwards via play() does not upgrade
    an already-audio-only join to a video one, which is why /vplay used to
    play sound with no picture. For video requests we skip the silence
    pre-join entirely so the very first play() call (in _stream_track) is
    the one that joins the call, and it always carries the real video —
    fixing the join at the source instead of trying to patch it after.
    """
    if video:
        return False

    if _active.get(chat_id):
        return False

    silence = await _get_silence_file()
    if not silence or not _pytgcalls:
        return False

    try:
        audio_quality = _get_audio_quality()
        sstream = MediaStream(silence, audio_parameters=audio_quality)
        _silence_playing[chat_id] = True
        await asyncio.wait_for(_pytgcalls.play(chat_id, sstream), timeout=8.0)
        _active[chat_id] = True
        LOGGER.debug("⚡ pre_join: instant VC join done for %d", chat_id)
        return True
    except asyncio.TimeoutError:
        LOGGER.debug("pre_join timed out for %d — real song will join VC normally", chat_id)
        _silence_playing.pop(chat_id, None)
        return False
    except Exception as e:
        LOGGER.debug("pre_join failed for %d: %s — real song will join VC normally", chat_id, e)
        _silence_playing.pop(chat_id, None)
        return False


async def abort_prejoin_if_idle(chat_id: int):
    """
    If we optimistically pre_join()'d a chat with silence but the search
    afterwards failed (song not found / too long / etc.), leave the call
    instead of leaving the bot sitting silently in the voice chat forever.
    No-ops if a real track ended up playing.
    """
    if _silence_playing.get(chat_id) and not get_current(chat_id):
        _active.pop(chat_id, None)
        _silence_playing.pop(chat_id, None)
        try:
            await _pytgcalls.leave_call(chat_id)
        except Exception:
            pass


async def force_play_stream(chat_id: int, track, video: bool = False) -> None:
    """Immediately play `track`, interrupting whatever is currently playing
    (used by /playforce and /vplayforce). Unlike play_stream(), this NEVER
    queues — it always jumps straight to streaming this track right now,
    regardless of what else is active or queued.
    """
    set_current(chat_id, track)

    if not _active.get(chat_id):
        await pre_join(chat_id, video=video)

    await _stream_track(chat_id, track, video=video)


async def play_stream(chat_id: int, track, video: bool = False) -> bool:
    """
    Start or queue a track.
    Returns True if playing now, False if queued.

    FIX 4 — CONCURRENT /play RACE:
    The per-chat lock (_play_locks) ensures that if two users issue /play at
    almost the same time, the second coroutine waits until the first has
    finished updating _active. Without the lock, both could read
    _active.get(chat_id) == False simultaneously, both set_current(), and both
    call _stream_track() — resulting in only one song playing while the other
    is silently lost. With the lock, the second request always sees
    _active == True and is correctly added to the queue.

    ⚡ INSTANT VC JOIN:
    If pre_join() already got the bot into the call with silence, this skips
    straight to streaming the real track (near-instant change_stream swap).
    If pre_join() was never called or failed, this falls back to joining
    with silence itself before streaming, exactly as before.
    """
    from melody.core.queue import add_to_queue

    lock = _get_play_lock(chat_id)
    async with lock:
        # A real track is already playing (not just our silence placeholder) —
        # queue this one instead of interrupting it.
        if _active.get(chat_id) and not _silence_playing.get(chat_id):
            add_to_queue(chat_id, track)
            return False

        set_current(chat_id, track)

        # If nobody pre-joined for us yet, do it now (keeps old callers working).
        if not _active.get(chat_id):
            await pre_join(chat_id, video=video)

    # ⚡ Download / pipe-stream the real song concurrently. If silence join
    # succeeded (either here or via an earlier pre_join()), change_stream
    # swaps in the audio the instant it's ready. If silence join failed,
    # _stream_track joins VC normally with the real song.
    # NOTE: _stream_track is kicked off OUTSIDE the lock so it doesn't block
    # the next /play request from queuing while the download is in progress.
    asyncio.create_task(_stream_track(chat_id, track, video=video))
    return True


async def pause_stream(chat_id: int):
    try:
        await _pytgcalls.pause(chat_id)
    except Exception as exc:
        await send_error_log(f"pause_stream failed in {chat_id}", exc)


async def resume_stream(chat_id: int):
    try:
        await _pytgcalls.resume(chat_id)
    except Exception as exc:
        await send_error_log(f"resume_stream failed in {chat_id}", exc)


async def skip_stream(chat_id: int):
    await _play_next(chat_id)


async def stop_stream(chat_id: int):
    """Stop playback, clear queue, leave voice chat."""
    clear_queue(chat_id)
    _active.pop(chat_id, None)
    _silence_playing.pop(chat_id, None)
    _is_video.pop(chat_id, None)
    _play_start_time.pop(chat_id, None)
    _seek_offset.pop(chat_id, None)
    try:
        await _pytgcalls.leave_call(chat_id)
    except Exception:
        pass


def get_playback_position(chat_id: int) -> int:
    """Best-effort elapsed seconds into the current track (baked-in seek
    offset + wall-clock time since the stream last started/was sought).
    Returns 0 if nothing is playing.
    """
    if chat_id not in _play_start_time:
        return 0
    elapsed = _seek_offset.get(chat_id, 0) + int(time.time() - _play_start_time[chat_id])
    track = get_current(chat_id)
    if track and track.duration:
        elapsed = min(elapsed, track.duration)
    return max(elapsed, 0)


async def seek_stream(chat_id: int, seconds: int) -> int:
    """Seek to an absolute position (in seconds) into the currently playing
    track.

    py-tgcalls 2.1.1 has no native seek/time-offset API (no seek_stream, no
    set_time), so real seeking is implemented by re-issuing play() with a
    fresh MediaStream whose ffmpeg command carries an input-side `-ss
    <seconds>` — this makes ffmpeg start decoding from that offset instead
    of from the beginning. Because play() on an already-active call swaps
    the stream in place (see _stream_track's docstring), this behaves like a
    real seek from the listener's perspective.

    Returns the resulting position in seconds. Raises RuntimeError if
    nothing is currently playing in this chat.
    """
    track = get_current(chat_id)
    if not track or not _pytgcalls or not _active.get(chat_id):
        raise RuntimeError("Nothing is playing right now.")

    seconds = max(0, int(seconds))
    if track.duration:
        seconds = min(seconds, max(track.duration - 1, 0))

    from melody.core.ytdl import download_audio

    video = _is_video.get(chat_id, False)
    filepath = await download_audio(track.video_id, audio_only=not video)

    audio_quality = _get_audio_quality()
    if video:
        stream = MediaStream(
            filepath,
            audio_parameters=audio_quality,
            video_parameters=_get_video_quality(),
            ffmpeg_parameters=f"-ss {seconds}",
        )
    else:
        stream = MediaStream(
            filepath,
            audio_parameters=audio_quality,
            ffmpeg_parameters=f"-ss {seconds}",
        )

    _silence_playing.pop(chat_id, None)
    await _pytgcalls.play(chat_id, stream)
    _active[chat_id] = True
    _seek_offset[chat_id] = seconds
    _play_start_time[chat_id] = time.time()
    return seconds


async def change_volume(chat_id: int, volume: int):
    set_volume_local(chat_id, volume)
    try:
        await _pytgcalls.change_volume_call(chat_id, volume)
    except Exception as exc:
        await send_error_log(f"change_volume failed in {chat_id}", exc)


def is_active(chat_id: int) -> bool:
    return bool(_active.get(chat_id))


def is_video_active(chat_id: int) -> bool:
    """Whether the call currently connected for `chat_id` was joined with
    video capability. Used by AutoPlay to keep replaying in the same mode
    the call was actually negotiated in, instead of silently guessing.
    """
    return bool(_is_video.get(chat_id))


async def get_participants(chat_id: int) -> list:
    try:
        return await _pytgcalls.get_participants(chat_id)
    except Exception:
        return []
