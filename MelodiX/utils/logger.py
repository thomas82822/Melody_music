#
# Copyright (C) 2021-2022 by TheY_CaIl_mE_OG@Github, < https://github.com/TheY_CaIl_mE_OG >.
#
# This file is part of < https://github.com/thomas82822/Melody_music > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/thomas82822/Melody_music/blob/master/LICENSE >
#
# All rights reserved.

from config import LOG, LOG_GROUP_ID
from MelodiX import app
from MelodiX.utils.database import is_on_off


async def play_logs(message, streamtype):
    if await is_on_off(LOG):
        if message.chat.username:
            chatusername = f"@{message.chat.username}"
        else:
            chatusername = "Private Group"
        logger_text = f"""
**MELODIX PLAY LOG**

**Chat:** {message.chat.title} [`{message.chat.id}`]
**User:** {message.from_user.mention}
**Username:** @{message.from_user.username}
**User ID:** `{message.from_user.id}`
**Chat Link:** {chatusername}

**Query:** {message.text}

**StreamType:** {streamtype}"""
        if message.chat.id != LOG_GROUP_ID:
            try:
                await app.send_message(
                    LOG_GROUP_ID,
                    f"{logger_text}",
                    disable_web_page_preview=True,
                )
            except:
                pass
        return
