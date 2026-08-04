"""
🤖 AutoPlay logic — fetch related videos from history
"""
from melody.logging import send_error_log
from melody.core.ytdl import get_related_videos, get_video_info
from melody.core.queue import Track, set_current
from utils.database import get_history, add_history, get_setting
from melody.config import Config


async def try_autoplay(chat_id: int):
    """Attempt to autoplay next related track for a chat."""
    try:
        from melody.core.call import play_stream, is_active
        from melody import bot

        if is_active(chat_id):
            return

        history = await get_history(chat_id)
        if not history:
            return

        last_id = history[-1]["id"]
        exclude_ids = [h["id"] for h in history]

        related = await get_related_videos(last_id, exclude_ids=exclude_ids)
        if not related:
            return

        top = related[0]
        info = await get_video_info(top["url"])
        if not info:
            return

        if info["duration"] > Config.MAX_DURATION:
            return

        track = Track(
            video_id=info["id"],
            title=info["title"],
            duration=info["duration"],
            stream_url=info["stream_url"],
            thumbnail=info["thumbnail"],
            uploader=info["uploader"],
            requester_id=0,
            requester_name="AutoPlay",
            requested_in=chat_id,
        )
        set_current(chat_id, track)
        await play_stream(chat_id, track)
        await add_history(chat_id, info["id"], info["title"])

        await bot.send_message(
            chat_id,
            f"🎵 **AutoPlay ▶️** `{info['title']}`\n_Melody ne sunwaya!_",
        )

    except Exception as exc:
        await send_error_log(f"try_autoplay failed in {chat_id}", exc)
