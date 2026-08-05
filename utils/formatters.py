"""
🎨 Text formatters and helpers
"""


def format_duration(seconds: int) -> str:
    """Convert seconds to mm:ss or hh:mm:ss."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_file_size(size_bytes: int) -> str:
    """Human-readable file size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def progress_bar(current: int, total: int, length: int = 15) -> str:
    """Simple ASCII progress bar."""
    if total == 0:
        return "▱" * length
    filled = int(length * current / total)
    bar = "▰" * filled + "▱" * (length - filled)
    percent = int(current / total * 100)
    return f"{bar} {percent}%"


def truncate(text: str, max_len: int = 50) -> str:
    """Truncate text with ellipsis."""
    return text[:max_len] + "…" if len(text) > max_len else text


def mention(user_id: int, name: str) -> str:
    """Telegram inline mention."""
    return f"[{name}](tg://user?id={user_id})"


import html as _html
import re as _re

# ── Telegram "quote message" formatting ─────────────────────────────────────
# Every user-facing card/message in the bot must render as a native Telegram
# quote block (the same grey vertical-bar quote strip Telegram uses for
# `<blockquote>`). All plain-text replies now go through quote_html() instead
# of relying on the old bare Markdown (**bold**) strings, which never had
# a quote strip around them.

_MD_PRE = _re.compile(r"```(?:\w+\n)?(.*?)```", _re.DOTALL)
_MD_BOLD = _re.compile(r"\*\*(.+?)\*\*")
_MD_CODE = _re.compile(r"`([^`]+?)`")
_MD_ITALIC = _re.compile(r"(?<!_)_([^_]+?)_(?!_)")


def md_to_html(text: str) -> str:
    """Convert the small subset of Markdown this bot used to use (```pre```,
    **bold**, `code`, _italic_) into HTML tags, so old plain-text strings
    render correctly once every message switches to parse_mode=HTML.

    BUG FIX (ENTITY_BOUNDS_INVALID / "can't parse entities"): code/pre spans
    are meant to hold verbatim text (usage hints like `/play <song name>`,
    raw shell output, exception messages, user queries, etc). Previously
    their captured content was inserted into <code>/<pre> tags UNESCAPED —
    any literal `<`, `>` or `&` inside (e.g. the `<song name>` placeholder
    in usage strings, or `<` in raw shell/exception output) was parsed by
    Telegram as the start of a real HTML tag/entity, which is invalid and
    makes the *entire* message fail to send with a 400 error. Escaping the
    captured text before wrapping it keeps it verbatim and always valid.
    """
    text = _MD_PRE.sub(lambda m: f"<pre>{_html.escape(m.group(1))}</pre>", text)
    text = _MD_BOLD.sub(r"<b>\1</b>", text)
    text = _MD_CODE.sub(lambda m: f"<code>{_html.escape(m.group(1))}</code>", text)
    text = _MD_ITALIC.sub(r"<i>\1</i>", text)
    return text


def quote_html(text: str, expandable: bool = False) -> str:
    """Wrap `text` (already HTML, or plain Markdown-ish text) in Telegram's
    native <blockquote> quote strip. Send with parse_mode=HTML.

    Converts legacy **bold** / `code` / _italic_ markers to HTML first, so
    call sites can keep writing the same strings they always did.
    """
    body = md_to_html(text)
    tag = "blockquote expandable" if expandable else "blockquote"
    close = "blockquote"
    return f"<{tag}>{body}</{close}>"


def mention_html(user_id: int, name: str) -> str:
    """Telegram inline mention using HTML parse mode."""
    return f'<a href="tg://user?id={user_id}">{_html.escape(name)}</a>'


# ── Telegram "premium animated emoji" + resilient sending ──────────────────
#
# BUG BEING FIXED (reported: "premium animated emoji work nahi kiya" +
# "telegram quote not working"):
#
# A previous change added <emoji id="..."> premium-emoji entities ONLY to
# the old, unused `MelodiX/` codebase — the bot that Heroku/Replit actually
# runs is `melody/` (see Procfile / .replit: `python -m melody`), which
# never had the feature and never had the bug fix either. That previous fix
# also proved *why* hand-typed emoji ids are dangerous: Telegram rejects an
# entire message outright when one <emoji id> entity doesn't resolve to a
# real custom-emoji document, which silently takes the surrounding
# <blockquote> "quote" down with it — one bad id breaks both symptoms at
# once.
#
# FIX: route every quote/emoji message in the LIVE bot through send_quote()
# below, which verifies each <emoji id> against Telegram first (dropping
# only the ones that don't resolve — the glyph and the blockquote always
# survive) and progressively degrades if the send still fails for any other
# reason, so the user always gets *a* reply instead of silence.
#
# We do NOT hand-type new custom-emoji ids here — that is exactly the
# anti-pattern that caused this bug. Real ids can only come from Telegram
# itself (a genuine premium emoji message). Use the owner-only /emojiid
# command (melody/plugins/owner/emoji_id.py) to extract real, verified ids
# from any message containing premium animated emoji, then wrap them with
# premium_emoji() below.

from pyrogram import enums as _enums
from pyrogram.errors import RPCError as _RPCError
import logging as _logging
from utils.telegram_html import verify_custom_emojis, strip_all_emoji_tags, strip_blockquote

_log = _logging.getLogger(__name__)


def premium_emoji(emoji_id: str, glyph: str) -> str:
    """Wrap `glyph` as a Telegram premium animated custom-emoji entity.

    Only ever send this through send_quote() (or verify_custom_emojis()
    directly) — that is what makes a wrong/rotated `emoji_id` fail safe
    (falls back to the plain glyph) instead of breaking the whole message.
    """
    return f'<emoji id="{emoji_id}">{glyph}</emoji>'


async def send_quote(handler, text: str, *, client=None, edit: bool = False, **kwargs):
    """Send (or edit) an HTML quote card — built with quote_html()/
    premium_emoji() — through Telegram safely.

    1. Verifies every <emoji id> against Telegram (pass `client` for a full
       check; without it, only impossible/out-of-range ids are dropped) —
       the <blockquote> quote formatting is never touched by this step.
    2. If the send still fails, retries with every <emoji> tag stripped.
    3. If it still fails, strips <blockquote> too and sends as plain text
       — so the user always gets *a* reply instead of silence.

    `handler` is anything with `.reply(text, parse_mode=..., **kwargs)`
    (e.g. a Message) — pass `edit=True` to call `.edit_text(...)` instead
    (e.g. editing a Message or CallbackQuery.message).

    `text` may already be full HTML (starting with <blockquote>, as most
    call sites in this bot write it inline) — in that case it's sent as-is.
    Anything else is auto-wrapped with quote_html() first, so plain text
    always renders as a native Telegram quote card.
    """
    if "<blockquote" not in text:
        text = quote_html(text)
    send = handler.edit_text if edit else handler.reply
    prepared = await verify_custom_emojis(client, text)
    try:
        return await send(prepared, parse_mode=_enums.ParseMode.HTML, **kwargs)
    except _RPCError as e:
        _log.warning("send_quote: retrying without premium emoji entities (%s)", e)

    stripped = strip_all_emoji_tags(prepared)
    try:
        return await send(stripped, parse_mode=_enums.ParseMode.HTML, **kwargs)
    except _RPCError as e:
        _log.error("send_quote: retrying as plain text (%s)", e)

    plain = strip_blockquote(stripped)
    return await send(plain, parse_mode=_enums.ParseMode.DISABLED, **kwargs)
