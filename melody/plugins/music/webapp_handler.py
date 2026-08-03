"""
🌐 Web App data handler — handles colored button actions from mini app

Note: filters.web_app_data is not available in Pyrogram 2.0.106, so we use
a custom filter that checks message.web_app_data directly.
"""
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.core.call import (
    pause_stream, resume_stream, skip_stream, stop_stream, change_volume
)
from melody.core.queue import (
    set_loop, shuffle_queue, get_volume, set_autoplay
)

# Custom filter — pyrogram 2.0.106 has no filters.web_app_data attribute
_web_app_filter = filters.create(lambda _, __, m: bool(getattr(m, "web_app_data", None)))


@bot.on_message(_web_app_filter)
async def handle_webapp(client: Client, message: Message):
    chat_id = message.chat.id
    action = message.web_app_data.data

    actions = {
        "pause":        lambda: pause_stream(chat_id),
        "resume":       lambda: resume_stream(chat_id),
        "skip":         lambda: skip_stream(chat_id),
        "stop":         lambda: stop_stream(chat_id),
        "loop_single":  lambda: set_loop(chat_id, "single"),
        "loop_all":     lambda: set_loop(chat_id, "all"),
        "shuffle":      lambda: shuffle_queue(chat_id),
        "mute":         lambda: change_volume(chat_id, 0),
        "vol_up":       lambda: change_volume(chat_id, min(200, get_volume(chat_id) + 20)),
        "vol_down":     lambda: change_volume(chat_id, max(1, get_volume(chat_id) - 20)),
        "autoplay_on":  lambda: set_autoplay(chat_id, True),
    }

    if action in actions:
        try:
            await actions[action]()
        except Exception:
            pass  # silent fail — errors go to LOG_GROUP only
