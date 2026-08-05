#
# Copyright (C) 2021-2022 by TheY_CaIl_mE_OG@Github, < https://github.com/TheY_CaIl_mE_OG >.
#
# This file is part of < https://github.com/thomas82822/Melody_music > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/thomas82822/Melody_music/blob/master/LICENSE >
#
# All rights reserved.
#
# YouTube-only version with cookies support.

import random
import string

from pyrogram import filters
from pyrogram.types import (InlineKeyboardMarkup, InputMediaPhoto,
                            Message)
from pytgcalls.exceptions import NoActiveGroupCall

import config
from config import BANNED_USERS, lyrical
from strings import get_command
from MelodiX import Telegram, YouTube, app
from MelodiX.core.call import MelodiX
from MelodiX.utils import seconds_to_min, time_to_seconds
from MelodiX.utils.channelplay import get_channeplayCB
from MelodiX.utils.database import is_video_allowed
from MelodiX.utils.decorators.language import languageCB
from MelodiX.utils.decorators.play import PlayWrapper
from MelodiX.utils.formatters import formats
from MelodiX.utils.inline.play import (livestream_markup,
                                          playlist_markup,
                                          slider_markup, track_markup)
from MelodiX.utils.inline.playlist import botplaylist_markup
from MelodiX.utils.logger import play_logs
from MelodiX.utils.stream.stream import stream

# Command
PLAY_COMMAND = get_command("PLAY_COMMAND")


@app.on_message(
    filters.command(PLAY_COMMAND)
    & filters.group
    & ~filters.edited
    & ~BANNED_USERS
)
@PlayWrapper
async def play_commnd(
    client,
    message: Message,
    _,
    chat_id,
    video,
    channel,
    playmode,
    url,
    fplay,
):
    mystic = await message.reply_text(
        _["play_2"].format(channel) if channel else _["play_1"]
    )
    plist_id = None
    slider = None
    plist_type = None
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    audio_telegram = (
        (
            message.reply_to_message.audio
            or message.reply_to_message.voice
        )
        if message.reply_to_message
        else None
    )
    video_telegram = (
        (
            message.reply_to_message.video
            or message.reply_to_message.document
        )
        if message.reply_to_message
        else None
    )

    # ── Telegram Audio File ──────────────────────────────────
    if audio_telegram:
        if audio_telegram.file_size > config.TG_AUDIO_FILESIZE_LIMIT:
            return await mystic.edit_text(_["play_5"])
        duration_min = seconds_to_min(audio_telegram.duration)
        if (audio_telegram.duration) > config.DURATION_LIMIT:
            return await mystic.edit_text(
                _["play_6"].format(config.DURATION_LIMIT_MIN, duration_min)
            )
        file_path = await Telegram.get_filepath(audio=audio_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(audio_telegram, audio=True)
            dur = await Telegram.get_duration(audio_telegram)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype="telegram",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else f"[{ex_type}] \n{e}"
                return await mystic.edit_text(
                    _["general_2"].format(err),
                    disable_web_page_preview=True,
                )
            return

    # ── Telegram Video File ──────────────────────────────────
    if video_telegram:
        if video_telegram.file_size > config.TG_VIDEO_FILESIZE_LIMIT:
            return await mystic.edit_text(_["play_5"])
        dur = seconds_to_min(video_telegram.duration) if hasattr(video_telegram, 'duration') and video_telegram.duration else "Unknown"
        file_path = await Telegram.get_filepath(video=video_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(video_telegram, audio=False)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype="telegram",
                    video=True,
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else f"[{ex_type}] \n{e}"
                return await mystic.edit_text(
                    _["general_2"].format(err),
                    disable_web_page_preview=True,
                )
            return

    # ── No query given ───────────────────────────────────────
    if not url:
        return await mystic.edit_text(_["play_3"])

    # ── YouTube Live Stream ──────────────────────────────────
    if await YouTube.exists(url):
        if "live" in url:
            mystic = await mystic.edit_text(
                _["play_1"] if not channel else _["play_2"].format(channel)
            )
            try:
                link = await YouTube.video(url)
            except:
                return await mystic.edit_text(_["str_3"])
            if link is None:
                return await mystic.edit_text(_["str_3"])
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    link,
                    chat_id,
                    user_name,
                    message.chat.id,
                    video=video,
                    streamtype="live_stream",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else f"[{ex_type}] \n{e}"
                return await mystic.edit_text(
                    _["general_2"].format(err),
                    disable_web_page_preview=True,
                )
            return

        # ── YouTube Playlist ─────────────────────────────────
        if "&list=" in url or "?list=" in url:
            try:
                details, plist_id = await YouTube.playlist(url, config.PLAYLIST_FETCH_LIMIT, user_id)
                plist_type = "yt"
            except:
                pass

        if plist_id:
            mystic = await mystic.edit_text(
                _["play_1"] if not channel else _["play_2"].format(channel)
            )
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    video=video,
                    streamtype="playlist",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else f"[{ex_type}] \n{e}"
                return await mystic.edit_text(
                    _["general_2"].format(err),
                    disable_web_page_preview=True,
                )
            return

        # ── Single YouTube Video ──────────────────────────────
        try:
            title, duration_min, duration_sec, thumbnail, vidid = await YouTube.details(url)
        except:
            return await mystic.edit_text(_["str_3"])
        if str(duration_min) == "None":
            return await mystic.edit_text(_["play_8"])
        if duration_sec > config.DURATION_LIMIT:
            return await mystic.edit_text(
                _["play_6"].format(config.DURATION_LIMIT_MIN, duration_min)
            )
        button = track_markup(_, vidid, user_id, channel, fplay)
        run = await mystic.edit_text(
            _["play_11"].format(title.title(), duration_min),
            reply_markup=InlineKeyboardMarkup(button),
        )
        db_val = {
            "title": title,
            "link": f"https://www.youtube.com/watch?v={vidid}",
            "vidid": vidid,
            "dur": duration_min,
            "thumb": thumbnail,
            "by": user_name,
            "og_chat_id": message.chat.id,
            "streamtype": "youtube",
        }
        # If lyrical mode, fetch title suggestion
        if playmode == "Direct":
            try:
                await stream(
                    _,
                    run,
                    user_id,
                    db_val,
                    chat_id,
                    user_name,
                    message.chat.id,
                    video=video,
                    streamtype="youtube",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else f"[{ex_type}] \n{e}"
                return await run.edit_text(
                    _["general_2"].format(err),
                    disable_web_page_preview=True,
                )
        return

    # ── YouTube Search ────────────────────────────────────────
    try:
        title, duration_min, duration_sec, thumbnail, vidid = await YouTube.details(url, videoid=False)
    except:
        return await mystic.edit_text(_["str_3"])
    if str(duration_min) == "None":
        return await mystic.edit_text(_["play_8"])
    if duration_sec > config.DURATION_LIMIT:
        return await mystic.edit_text(
            _["play_6"].format(config.DURATION_LIMIT_MIN, duration_min)
        )
    button = track_markup(_, vidid, user_id, channel, fplay)
    run = await mystic.edit_text(
        _["play_11"].format(title.title(), duration_min),
        reply_markup=InlineKeyboardMarkup(button),
    )
    db_val = {
        "title": title,
        "link": f"https://www.youtube.com/watch?v={vidid}",
        "vidid": vidid,
        "dur": duration_min,
        "thumb": thumbnail,
        "by": user_name,
        "og_chat_id": message.chat.id,
        "streamtype": "youtube",
    }
    if playmode == "Direct":
        try:
            await stream(
                _,
                run,
                user_id,
                db_val,
                chat_id,
                user_name,
                message.chat.id,
                video=video,
                streamtype="youtube",
                forceplay=fplay,
            )
        except Exception as e:
            ex_type = type(e).__name__
            err = e if ex_type == "AssistantErr" else f"[{ex_type}] \n{e}"
            return await run.edit_text(
                _["general_2"].format(err),
                disable_web_page_preview=True,
            )


# ── Play Callback (slider / track buttons) ──────────────────

PLAY_CB = get_command("PLAY_CB")


@app.on_callback_query(filters.regex(PLAY_CB) & ~BANNED_USERS)
@languageCB
async def play_cb(client, CallbackQuery, _):
    data = CallbackQuery.data.split("|")
    what = data[1]
    vidid = data[2]
    user_id = int(data[3])
    chat_id = int(data[4])
    video = data[5]
    channel = data[6]
    fplay = True if data[7] == "f" else None
    cplay = True if channel == "c" else None
    query = f"https://www.youtube.com/watch?v={vidid}"

    if what == "P":
        # Stream this track
        title, duration_min, duration_sec, thumbnail, _ = await YouTube.details(query)
        if duration_sec > config.DURATION_LIMIT:
            return await CallbackQuery.answer(_["play_6"].format(config.DURATION_LIMIT_MIN, duration_min), show_alert=True)
        db_val = {
            "title": title,
            "link": query,
            "vidid": vidid,
            "dur": duration_min,
            "thumb": thumbnail,
            "by": (await CallbackQuery.get_users(user_id)).first_name,
            "og_chat_id": CallbackQuery.message.chat.id,
            "streamtype": "youtube",
        }
        try:
            await stream(
                _,
                CallbackQuery.message,
                user_id,
                db_val,
                chat_id,
                (await CallbackQuery.get_users(user_id)).first_name,
                CallbackQuery.message.chat.id,
                video=True if video == "v" else None,
                streamtype="youtube",
                forceplay=fplay,
            )
        except Exception as e:
            ex_type = type(e).__name__
            err = e if ex_type == "AssistantErr" else f"[{ex_type}] \n{e}"
            return await CallbackQuery.answer(
                _["general_2"].format(err), show_alert=True
            )
        await CallbackQuery.answer()

    elif what in ("F", "B"):
        # Slider
        rtype = int(data[8])
        if what == "F":
            query_type = 0 if rtype == 9 else int(rtype + 1)
        else:
            query_type = 9 if rtype == 0 else int(rtype - 1)
        try:
            await CallbackQuery.answer(_["playcb_2"])
        except:
            pass
        title, duration_min, thumbnail, vidid = await YouTube.slider(
            query, query_type
        )
        buttons = slider_markup(
            _, vidid, user_id, query, query_type, cplay, fplay
        )
        med = InputMediaPhoto(
            media=thumbnail,
            caption=_["play_11"].format(title.title(), duration_min),
        )
        return await CallbackQuery.edit_message_media(
            media=med, reply_markup=InlineKeyboardMarkup(buttons)
        )
