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
