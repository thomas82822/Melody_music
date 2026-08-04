"""
🔥 Animated status messages (requirement #5)

Replaces the old static "🔍 Searching..." placeholder with a message that
cycles through random fire/celebration emojis while real work (VC join +
yt-dlp search) happens in the background — purely cosmetic, never blocks
or slows down the actual command.
"""
import asyncio
import random
from pyrogram.errors import RPCError

FIRE_EMOJIS = [
    "🔥", "💥", "⚡", "✨", "🎆", "🎇", "🌟", "💫", "🎉", "🚀", "🎶", "🪩", "🎵", "💃",
]


class AnimatedStatus:
    """
    Edits `message` every `interval` seconds with a random emoji frame until
    `.stop()` is called. Runs as its own background asyncio task, so
    starting/stopping it never adds latency to the caller's real work.
    """

    def __init__(self, message, label: str = "Getting your vibe ready", interval: float = 0.6):
        self._message = message
        self._label = label
        self._interval = interval
        self._task: "asyncio.Task | None" = None
        self._stopped = asyncio.Event()

    def start(self) -> "AnimatedStatus":
        self._task = asyncio.create_task(self._loop())
        return self

    async def _loop(self):
        last = None
        while not self._stopped.is_set():
            emoji = random.choice(FIRE_EMOJIS)
            while emoji == last and len(FIRE_EMOJIS) > 1:
                emoji = random.choice(FIRE_EMOJIS)
            last = emoji
            try:
                await self._message.edit(f"{emoji} {self._label} {emoji}")
            except RPCError:
                pass
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=self._interval)
            except asyncio.TimeoutError:
                pass

    async def stop(self):
        self._stopped.set()
        if self._task:
            try:
                await self._task
            except Exception:
                pass
            self._task = None
