"""
🛡️ Resilient sender for "premium animated emoji" + native Telegram "quote"
(<blockquote>) formatted messages.

BUG BEING FIXED
----------------
A previous change wrapped several cards in <blockquote> and sprinkled
<emoji id="..."> "premium animated emoji" entities through them, but never
verified the emoji ids were real Telegram custom-emoji documents:

- One id (``95282968352862527007``) is 20 digits — outside the signed
  64-bit range Telegram document ids live in — so it can never be valid.
- The rest are plausible-looking but were hand-typed placeholders, not ids
  pulled from a real custom emoji pack the bot can see.

Telegram rejects a message outright when one of its entities points at a
custom emoji id it doesn't recognise (``CUSTOM_EMOJI_INVALID`` /
``MSG_ENTITIES_INVALID``-style errors). Because the whole request fails,
neither the emoji *nor* the surrounding <blockquote> "quote" render — the
user just sees the old message (or nothing), which is exactly the two
symptoms reported ("premium animated emoji" not working *and* the
Telegram "quote" not working): both are collateral damage of one bad id.

FIX
---
Before sending, verify every <emoji id="..."> against Telegram
(``get_custom_emoji_stickers``) and drop only the ones that don't resolve,
falling back to their plain glyph. The <blockquote> "quote" formatting
always survives. If the send still fails for an unrelated reason, we
retry with formatting stripped entirely so the user always gets *a*
reply instead of silence.
"""

import logging
import re
from typing import Awaitable, Callable, Dict, Optional

from pyrogram.enums import ParseMode
from pyrogram.errors import RPCError

log = logging.getLogger(__name__)

_EMOJI_TAG_RE = re.compile(r"<emoji id=[\"']?(-?\d+)[\"']?>(.*?)</emoji>", re.DOTALL)
_INT64_MAX = 2**63 - 1

# Per-client cache of {custom_emoji_id: is_valid}, so we only ever hit
# Telegram once per id instead of on every message.
_verified_cache: Dict[int, Dict[int, bool]] = {}


def strip_out_of_range_emoji(text: str) -> str:
    """Drop <emoji> tags whose id can't possibly be a real Telegram document
    id (those are signed 64-bit integers) without needing any API call."""

    def _sub(match: "re.Match[str]") -> str:
        emoji_id, inner = match.group(1), match.group(2)
        if abs(int(emoji_id)) > _INT64_MAX:
            return inner
        return match.group(0)

    return _EMOJI_TAG_RE.sub(_sub, text)


def strip_all_emoji_tags(text: str) -> str:
    """Unwrap every <emoji id="...">X</emoji> down to the plain glyph X."""
    return _EMOJI_TAG_RE.sub(lambda m: m.group(2), text)


def strip_blockquote(text: str) -> str:
    """Remove <blockquote>/<blockquote expandable> wrapping, last-resort
    fallback when even the sanitized HTML fails to send."""
    return (
        text.replace("<blockquote expandable>", "")
        .replace("<blockquote>", "")
        .replace("</blockquote>", "")
    )


async def verify_custom_emojis(client, text: str) -> str:
    """Check every <emoji id> referenced in `text` against Telegram and
    silently fall back to the plain glyph for any id that isn't a real,
    resolvable custom emoji — so one bad/fake id can never sink the whole
    message (and the <blockquote> quote around it)."""
    text = strip_out_of_range_emoji(text)

    if client is None:
        return text

    ids = {int(m.group(1)) for m in _EMOJI_TAG_RE.finditer(text)}
    if not ids:
        return text

    cache = _verified_cache.setdefault(id(client), {})
    unknown = [i for i in ids if i not in cache]
    if unknown:
        found_ids: set = set()
        try:
            stickers = await client.get_custom_emoji_stickers(unknown)
            for requested_id, sticker in zip(unknown, stickers):
                # get_custom_emoji_stickers returns results in the same
                # order as the requested ids for every id Telegram resolved.
                if sticker is not None:
                    found_ids.add(requested_id)
        except RPCError as e:
            log.warning("Could not verify custom emoji ids %s: %s", unknown, e)
        except Exception as e:  # defensive: never let verification crash a send
            log.warning("Unexpected error verifying custom emoji ids %s: %s", unknown, e)
        for i in unknown:
            cache[i] = i in found_ids

    def _sub(match: "re.Match[str]") -> str:
        emoji_id, inner = int(match.group(1)), match.group(2)
        return match.group(0) if cache.get(emoji_id) else inner

    return _EMOJI_TAG_RE.sub(_sub, text)


async def safe_html_action(
    action: Callable[..., Awaitable],
    text: str,
    *,
    client=None,
    **kwargs,
) -> object:
    """Run `action(text, parse_mode=ParseMode.HTML, **kwargs)` after
    sanitizing premium-emoji entities, degrading gracefully instead of
    letting a bad entity kill the whole message:

    1. Verify <emoji id> tags against Telegram; drop the invalid ones
       (the <blockquote> "quote" formatting is preserved).
    2. If the send still fails, strip every <emoji> tag and retry.
    3. If it still fails, strip <blockquote> too and send as plain text.

    `action` should be a callable such as
    ``lambda t, **kw: message.reply_text(t, **kw)`` — pass through only the
    text and formatting-related kwargs (parse_mode is set here).
    """
    prepared = await verify_custom_emojis(client, text)
    try:
        return await action(prepared, parse_mode=ParseMode.HTML, **kwargs)
    except RPCError as e:
        log.warning("safe_html_action: send failed with emoji entities (%s), retrying without them", e)

    stripped = strip_all_emoji_tags(prepared)
    try:
        return await action(stripped, parse_mode=ParseMode.HTML, **kwargs)
    except RPCError as e:
        log.error("safe_html_action: send failed without emoji entities too (%s), falling back to plain text", e)

    plain = strip_blockquote(stripped)
    return await action(plain, parse_mode=ParseMode.DISABLED, **kwargs)
