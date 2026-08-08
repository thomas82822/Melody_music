"""
▶️ /play and /vplay commands
BUG FIX: @error_handler moved OUTSIDE @admin_or_auth so DB errors are also caught
BUG FIX: Removed duplicate callback handlers (pause/resume/skip/stop/queue/lyrics
         are already registered in controls.py — having them here too caused
         duplicate handler registration and unpredictable behaviour)
BUG FIX: ENTITY_BOUNDS_INVALID — switched all dynamic-text messages to HTML
         parse_mode with html.escape() so song titles / uploader names that
         contain Markdown special characters (* _ ` [ etc.) never produce
         malformed entities.  Slicing a title string mid-Markdown-token was
         the direct trigger for [400 ENTITY_BOUNDS_INVALID].

⚡ FAST & RELIABLE /play (requirement #4):
   The bot now joins the voice chat (pre_join) in PARALLEL with the yt-dlp
   search instead of after it — the multi-second search is no longer on the
   critical path to "bot is in the call". As soon as the search resolves,
   the real track swaps in via change_stream (near-instant).

🔥 Animated status (requirement #5):
   The static "🔍 Searching..." message is replaced by AnimatedStatus, which
   cycles random fire/celebration emojis while the join+search race runs.
"""
import asyncio
import html
import urllib.parse
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from melody import bot
from melody.config import Config
from melody.core.ytdl import get_video_info, download_replied_media, has_playable_media
from melody.core.queue import Track, add_to_queue, is_autoplay_on
from melody.core.call import play_stream, force_play_stream, pre_join, abort_prejoin_if_idle
from melody.logging import log_activity
from utils.database import add_history
from utils.decorators import admin_or_auth, channel_admin_or_auth, error_handler
from utils.formatters import format_duration, quote_html
from utils.thumbnails import make_thumbnail, fetch_dp, get_bot_dp, get_bot_identity
from utils.animation import AnimatedStatus
from strings.themes import BLUE, RED, GREEN, btn


def get_play_buttons(
    chat_title: str,
    autoplay_on: bool = False,
    bot_username: "str | None" = None,
    bot_name: str = "Melody",
) -> InlineKeyboardMarkup:
    encoded_title = urllib.parse.quote(chat_title[:30])
    webapp_url = f"{Config.WEBAPP_URL}?chat={encoded_title}" if Config.WEBAPP_URL else "https://t.me"
    autoplay_label = f"🔁 AutoPlay: {'ON 🟢' if autoplay_on else 'OFF 🔴'}"
    # REQUEST: "gc me har time inline buttons me [bot ka] uska name add krna"
    # — every play card sent in a group now carries a branding row with the
    # bot's own name, linking straight to it (falls back to a harmless
    # no-op button if BOT_USERNAME was never configured / get_me() failed).
    bot_branding_button = (
        InlineKeyboardButton(btn(f"🎧 {bot_name}", GREEN), url=f"https://t.me/{bot_username}")
        if bot_username else
        InlineKeyboardButton(btn(f"🎧 {bot_name}", GREEN), callback_data="noop")
    )
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(btn("⏸ Pause", RED),  callback_data="pause"),
            InlineKeyboardButton(btn("⏭ Skip", BLUE),   callback_data="skip"),
            InlineKeyboardButton(btn("⏹ Stop", RED),   callback_data="stop"),
        ],
        [
            InlineKeyboardButton(btn("🎛 Colored Controls", GREEN), web_app=WebAppInfo(url=webapp_url)),
        ] if Config.WEBAPP_URL else [],
        [
            InlineKeyboardButton(btn("📋 Queue", BLUE),  callback_data="queue"),
            InlineKeyboardButton(btn(autoplay_label, GREEN), callback_data="autoplay_toggle"),
        ],
        [bot_branding_button],
    ])


async def _play_core(client: Client, message: Message, video: bool = False, force: bool = False):
    query = " ".join(message.command[1:]) if len(message.command) > 1 else None
    chat = message.chat
    user = message.from_user

    # 🏷 Tag-to-play: reply /play or /vplay to any audio/video/voice message
    # (or an audio/video document) to stream that exact file — no text query
    # needed. This takes priority over a text query when both are present.
    replied = message.reply_to_message
    tagged = has_playable_media(replied)

    if not query and not tagged:
        usage_cmd = "/cplay" if chat.type == enums.ChatType.CHANNEL else "/play"
        await message.reply(
            quote_html(
                f"**Usage:** `{usage_cmd} <song name or YouTube URL>`\n"
                f"Ya kisi audio/video message ko reply karke sirf `{usage_cmd}` bhejo."
            ),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    # Channel posts have no from_user — attribute the request to the channel
    # itself so requester_id/name/mention/dp fetching all stay well-defined.
    requester_id = user.id if user else chat.id
    requester_name = user.first_name if user else (chat.title or "Channel")
    requester_mention = user.mention if user else html.escape(requester_name)

    processing = await message.reply(
        quote_html("🔥 Getting your vibe ready..."), parse_mode=enums.ParseMode.HTML
    )
    anim = AnimatedStatus(processing, "Getting your vibe ready").start()

    # ⚡ Kick off the VC join AND the profile-photo downloads immediately, in
    # parallel with the yt-dlp search — none of this waits on the others.
    join_task = asyncio.create_task(pre_join(chat.id, video=video))
    bot_dp_task = asyncio.create_task(get_bot_dp(client))
    user_dp_task = asyncio.create_task(fetch_dp(client, requester_id))

    try:
        if tagged:
            info = await download_replied_media(client, replied, video=video)
        else:
            info = await get_video_info(query)

        if not info:
            await abort_prejoin_if_idle(chat.id)
            await anim.stop()
            fail_msg = "❌ Ye tagged file play nahi ho payi 🌸" if tagged else "❌ Song nahi mili 🌸"
            await processing.edit(quote_html(fail_msg), parse_mode=enums.ParseMode.HTML)
            return

        track = Track(
            video_id=info["id"],
            title=info["title"],
            duration=info["duration"],
            stream_url=info["stream_url"],
            thumbnail=info["thumbnail"],
            uploader=info["uploader"],
            requester_id=requester_id,
            requester_name=requester_name,
            requested_in=chat.id,
            # BUG FIX: record whether this was /play or /vplay on the track
            # itself so the video intent survives queuing / auto-advance /
            # loop-single instead of silently reverting to audio-only.
            video=video,
        )

        # Make sure the pre-join attempt has finished before play_stream()
        # decides whether the chat is "already active" — it's usually done
        # well before the search above resolves.
        await join_task

        if force:
            await force_play_stream(chat.id, track, video=video)
            playing_now = True
        else:
            playing_now = await play_stream(chat.id, track, video=video)
        await add_history(chat.id, info["id"], info["title"])

        activity_label = "Force Played" if force else ("Now Playing" if playing_now else "Queued")
        asyncio.create_task(log_activity(
            f"🎵 <b>{activity_label}</b>\n"
            f"• Song: <code>{html.escape(info['title'][:60])}</code>\n"
            f"• Requested by: {html.escape(requester_name or 'Unknown')} (<code>{requester_id}</code>)\n"
            f"• Chat: {html.escape(chat.title or 'Private')} (<code>{chat.id}</code>)"
        ))

        status_label = "Force Played" if force else ("Now Playing" if playing_now else "Added to Queue")
        safe_title    = html.escape(info["title"][:50])
        safe_uploader = html.escape(info["uploader"])
        safe_duration = html.escape(format_duration(info["duration"]))

        bot_dp_path, user_dp_path = await asyncio.gather(bot_dp_task, user_dp_task)
        bot_username, bot_name = await get_bot_identity(client)
        autoplay_on = await is_autoplay_on(chat.id)
        play_buttons = get_play_buttons(chat.title or "", autoplay_on, bot_username, bot_name)

        safe_group = html.escape((chat.title or "Private")[:60])
        caption = (
            f"<blockquote>🎶 <b>{html.escape(status_label)}</b>\n\n"
            f"<b>{safe_title}</b>\n"
            f"👤 <code>{safe_uploader}</code>  ⏱ <code>{safe_duration}</code>\n"
            f"🏠 {safe_group}\n"
            f"🙋 Requested by {requester_mention}</blockquote>"
        )
        try:
            thumb_path = await make_thumbnail(
                song_title=info["title"],
                artist=info["uploader"],
                duration=format_duration(info["duration"]),
                requester_name=requester_name,
                group_name=chat.title or "Private",
                owner_name=Config.OWNER_NAME,
                yt_thumbnail_url=info["thumbnail"],
                requester_dp_path=user_dp_path,
                bot_dp_path=bot_dp_path,
            )
            await anim.stop()
            # BUG FIX: previously processing.delete() ran BEFORE reply_photo,
            # so when reply_photo failed (CHAT_SEND_PHOTOS_FORBIDDEN — the group
            # doesn't allow photos), the fallback tried to .edit() the already-
            # deleted message → MESSAGE_ID_INVALID crash. Now we send the photo
            # FIRST and only delete the processing message on success.
            await message.reply_photo(
                thumb_path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML,
                reply_markup=play_buttons,
            )
            await processing.delete()
        except Exception as thumb_exc:
            from melody.logging import send_error_log
            await send_error_log(f"make_thumbnail / reply_photo failed in {chat.id}", thumb_exc)
            status = "Force Played ⚡" if force else ("Now Playing ▶️" if playing_now else "Added to Queue 📋")
            await anim.stop()
            # BUG FIX: the processing message may still exist (photo send
            # failed before delete), so edit it. But if it was already deleted
            # (partial success path), fall back to a new reply.
            try:
                await processing.edit(
                    quote_html(
                        f"🎵 <b>{html.escape(status)}</b>\n\n"
                        f"<code>{safe_title}</code>\n"
                        f"👤 <code>{safe_uploader}</code>  ⏱ <code>{safe_duration}</code>\n"
                        f"🏠 {html.escape((chat.title or 'Private')[:60])}"
                    ),
                    parse_mode=enums.ParseMode.HTML,
                    reply_markup=play_buttons,
                )
            except Exception:
                await message.reply(
                    quote_html(
                        f"🎵 <b>{html.escape(status)}</b>\n\n"
                        f"<code>{safe_title}</code>\n"
                        f"👤 <code>{safe_uploader}</code>  ⏱ <code>{safe_duration}</code>\n"
                        f"🏠 {html.escape((chat.title or 'Private')[:60])}"
                    ),
                    parse_mode=enums.ParseMode.HTML,
                    reply_markup=play_buttons,
                )
    finally:
        await anim.stop()


# BUG FIX: @error_handler is OUTER decorator — catches errors from admin_or_auth too
@bot.on_message(filters.command("play") & filters.group)
@error_handler
@admin_or_auth
async def play_cmd(client: Client, message: Message):
    await _play_core(client, message, video=False)


@bot.on_message(filters.command("vplay") & filters.group)
@error_handler
@admin_or_auth
async def vplay_cmd(client: Client, message: Message):
    await _play_core(client, message, video=True)


# ─── Force play — interrupts whatever is currently playing/queued ────────────

@bot.on_message(filters.command("playforce") & filters.group)
@error_handler
@admin_or_auth
async def playforce_cmd(client: Client, message: Message):
    await _play_core(client, message, video=False, force=True)


@bot.on_message(filters.command("vplayforce") & filters.group)
@error_handler
@admin_or_auth
async def vplayforce_cmd(client: Client, message: Message):
    await _play_core(client, message, video=True, force=True)


# ─── Channel play — /play and /vplay usable directly inside a channel ────────
# Channels can host a voice chat exactly like groups (py-tgcalls joins by
# chat_id either way); only the permission model differs, since a channel
# "message" is usually a post authored by the channel itself rather than a
# specific user. channel_admin_or_auth() handles that distinction.

@bot.on_message(filters.command("cplay") & filters.channel)
@error_handler
@channel_admin_or_auth
async def cplay_cmd(client: Client, message: Message):
    await _play_core(client, message, video=False)


@bot.on_message(filters.command("cvplay") & filters.channel)
@error_handler
@channel_admin_or_auth
async def cvplay_cmd(client: Client, message: Message):
    await _play_core(client, message, video=True)
