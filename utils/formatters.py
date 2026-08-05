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
