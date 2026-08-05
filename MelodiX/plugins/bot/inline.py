#
# Copyright (C) 2021-2022 by TheY_CaIl_mE_OG@Github, < https://github.com/TheY_CaIl_mE_OG >.
#
# This file is part of < https://github.com/thomas82822/Melody_music > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/thomas82822/Melody_music/blob/master/LICENSE >
#
# All rights reserved.

from pyrogram.types import (InlineKeyboardButton,
                            InlineKeyboardMarkup,
                            InlineQueryResultPhoto)
from youtubesearchpython.__future__ import VideosSearch

from config import BANNED_USERS, MUSIC_BOT_NAME
from MelodiX import app
from MelodiX.utils.inlinequery import answer


@app.on_inline_query(~BANNED_USERS)
async def inline_query_handler(client, query):
    text = query.query.strip().lower()
    answers = []
    if text.strip() == "":
        try:
            await client.answer_inline_query(
                query.id, results=answer, cache_time=10
            )
        except:
            return
    else:
        a = VideosSearch(text, limit=20)
        result = (await a.next()).get("result")
        for x in range(15):
            title = (result[x]["title"]).title()
            duration = result[x]["duration"]
            views = result[x]["viewCount"]["short"]
            thumbnail = result[x]["thumbnails"][0]["url"].split("?")[
                0
            ]
            channellink = result[x]["channel"]["link"]
            channel = result[x]["channel"]["name"]
            link = result[x]["link"]
            published = result[x]["publishedTime"]
            description = f"{views} | {duration} Mins | {channel}  | {published}"
            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="🎥 Watch on Youtube",
                            url=link,
                        )
                    ],
                ]
            )
            searched_text = f"""<blockquote>
<emoji id='95282968352862527007'>❇️</emoji>**Title:** [{title}]({link})

<emoji id='5098255325723625291'>⏳</emoji>**Duration:** {duration} Mins
<emoji id='6298429115628259446'>👀</emoji>**Views:** `{views}`
<emoji id='95282968352862527007'>⏰</emoji>**Published Time:** {published}
<emoji id='5098567638565520047'>🎥</emoji>**Channel Name:** {channel}
<emoji id='5397971251873873206'>📎</emoji>**Channel Link:** [Visit From Here]({channellink})

__Reply with /play on this searched message to stream it on voice chat.__

<emoji id='5337260982911655617'>⚡</emoji>️ ** Inline Search By {MUSIC_BOT_NAME} **</blockquote>"""
            answers.append(
                InlineQueryResultPhoto(
                    photo_url=thumbnail,
                    title=title,
                    thumb_url=thumbnail,
                    description=description,
                    caption=searched_text,
                    reply_markup=buttons,
                )
            )
        try:
            return await client.answer_inline_query(
                query.id, results=answers
            )
        except:
            return
