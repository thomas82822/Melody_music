"""
🌍 Global "premium emoji everywhere" patch.

WHY THIS EXISTS
----------------
`utils/formatters.premium_emoji()` + `PREMIUM_EMOJI_IDS` only ever covered
10 hand-picked headline strings (start/about/ping/stats/pause/resume/skip/
stop/nowplaying/queue). Every other plugin (~40 files, ~500+ raw glyphs —
help menus, admin commands, error messages, panel, ytdl errors, etc.) still
sent plain-text emoji, so premium emoji only ever "worked" in a few places.

Hand-editing every call site to wrap its glyphs is high-effort and high
regression-risk for a live bot we can't run end-to-end here. Instead we
intercept at the lowest common layer: EVERY outgoing text/caption in
Pyrogram ultimately flows through `Client.send_message`,
`Client.edit_message_text`, or `Client.send_photo` — `Message.reply`,
`Message.reply_text`, `Message.edit`, `Message.edit_text`, and
`Message.reply_photo` are all thin wrappers around these three. Patching
just these three functions therefore covers every send path in the bot
(present AND future — new plugins get this for free).

WHAT THE PATCH DOES
--------------------
For the text/caption argument only, it runs the existing
`verify_custom_emojis()` pipeline (which itself calls `auto_premium_emoji()`
first — see utils/telegram_html.py) — i.e. exactly the same fail-safe
wrap-then-verify-against-Telegram-then-fall-back-to-plain-glyph flow that
`send_quote()` already used for the original 10 headline strings, just
applied globally now. Nothing else about the call (parse_mode, markup,
media, etc.) is touched, so existing behavior for non-text arguments and
already-verified `<emoji>` tags is unchanged. Idempotent: text that has
already gone through `send_quote()`/`premium_emoji()` will not be
double-wrapped (auto_premium_emoji skips glyphs already inside an
<emoji>...</emoji> span).

Call `apply_emoji_patch()` exactly once, before the bot starts polling
(done in `melody/__init__.py`, right after `create_clients()`).
"""

import functools
import inspect
import logging

from pyrogram import Client

from utils.telegram_html import verify_custom_emojis

log = logging.getLogger(__name__)

_PATCHED_METHODS = (
    ("send_message", "text"),
    ("edit_message_text", "text"),
    ("send_photo", "caption"),
)

_applied = False


def _wrap(method_name: str, param_name: str) -> None:
    original = getattr(Client, method_name)
    if getattr(original, "_emoji_patched", False):
        return  # already patched (e.g. apply_emoji_patch called twice)

    sig = inspect.signature(original)

    @functools.wraps(original)
    async def wrapper(self, *args, **kwargs):
        bound = sig.bind_partial(self, *args, **kwargs)
        bound.apply_defaults()
        value = bound.arguments.get(param_name)
        if isinstance(value, str) and value:
            try:
                bound.arguments[param_name] = await verify_custom_emojis(self, value)
            except Exception:
                # Never let emoji wrapping itself break a real send — fall
                # back to the original, unwrapped text so the message still
                # goes out. Do NOT catch errors from original() itself; those
                # are real API errors (e.g. CHANNEL_INVALID) that must
                # propagate to the caller.
                log.exception("emoji_patch: falling back to plain %s()", method_name)
        return await original(*bound.args, **bound.kwargs)

    wrapper._emoji_patched = True
    setattr(Client, method_name, wrapper)


def apply_emoji_patch() -> None:
    """Patch pyrogram.Client so every outgoing message/caption is run
    through the premium-emoji auto-wrap + verify pipeline. Idempotent —
    safe to call more than once."""
    global _applied
    if _applied:
        return
    for method_name, param_name in _PATCHED_METHODS:
        _wrap(method_name, param_name)
    _applied = True
    log.info("emoji_patch: premium-emoji auto-wrap active on %s", 
              ", ".join(m for m, _ in _PATCHED_METHODS))
