"""
🌐 Web App data handler — handles actions sent back from any Mini App page.

Two Mini App pages exist:
  - `docs/index.html` — playback controls, sends plain action strings
    (e.g. "pause", "skip").
  - `docs/menu.html`  — generic colored menu grid (see `strings/webmenu.py`),
    sends "<menu_id>:<action>" (e.g. "help:admin").

Note: filters.web_app_data is not available in Pyrogram 2.0.106, so we use
a custom filter that checks message.web_app_data directly.
"""
from pyrogram import Client, filters, enums
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

_CONTROL_ACTIONS = {
    "pause":        lambda chat_id: pause_stream(chat_id),
    "resume":       lambda chat_id: resume_stream(chat_id),
    "skip":         lambda chat_id: skip_stream(chat_id),
    "stop":         lambda chat_id: stop_stream(chat_id),
    "loop_single":  lambda chat_id: set_loop(chat_id, "single"),
    "loop_all":     lambda chat_id: set_loop(chat_id, "all"),
    "shuffle":      lambda chat_id: shuffle_queue(chat_id),
    "mute":         lambda chat_id: change_volume(chat_id, 0),
    "vol_up":       lambda chat_id: change_volume(chat_id, min(200, get_volume(chat_id) + 20)),
    "vol_down":     lambda chat_id: change_volume(chat_id, max(1, get_volume(chat_id) - 20)),
    "autoplay_on":  lambda chat_id: set_autoplay(chat_id, True),
}


async def _handle_help_menu(message: Message, action: str) -> None:
    from melody.plugins.misc.help import render_help_category

    if action == "close":
        return

    text, markup = render_help_category(action)
    if text:
        await message.reply(text, parse_mode=enums.ParseMode.HTML, reply_markup=markup)


@bot.on_message(_web_app_filter)
async def handle_webapp(client: Client, message: Message):
    chat_id = message.chat.id
    data = message.web_app_data.data

    try:
        if ":" in data:
            menu_id, action = data.split(":", 1)
            if menu_id == "help":
                await _handle_help_menu(message, action)
                return
            # Unknown menu id — ignore rather than guess.
            return

        if data in _CONTROL_ACTIONS:
            await _CONTROL_ACTIONS[data](chat_id)
    except Exception:
        pass  # silent fail — errors go to LOG_GROUP only
