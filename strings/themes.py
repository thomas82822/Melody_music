"""
🎨 Theme strings — Modi-Meloni color palette
"""

# ─────────────────────────────────────────────────────────────────────────────
#  Stylized "fancy font" text — Mathematical Bold Italic Unicode block
#  (matches the requested style, e.g. "𝒔𝒋𝒌𝒔𝒔𝒔𝒃𝒔𝒔𝒔𝒏𝒔")
# ─────────────────────────────────────────────────────────────────────────────
_FANCY_MAP: dict[str, str] = {}
for _i, _c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    _FANCY_MAP[_c] = chr(0x1D468 + _i)
for _i, _c in enumerate("abcdefghijklmnopqrstuvwxyz"):
    _FANCY_MAP[_c] = chr(0x1D482 + _i)
for _i, _c in enumerate("0123456789"):
    _FANCY_MAP[_c] = chr(0x1D7CE + _i)


def fancy(text: str) -> str:
    """Render text in bold-italic Unicode "fancy font" (𝑴𝒆𝒍𝒐𝒅𝒚 style).

    Falls back to the original character for anything outside A-Z/a-z/0-9
    (spaces, emoji, punctuation) so formatting/links keep working.
    """
    return "".join(_FANCY_MAP.get(ch, ch) for ch in text)


# ─────────────────────────────────────────────────────────────────────────────
#  Inline button color-coding — matches the reference screenshot's palette.
#  Bot API inline buttons can't carry a real background color, so every
#  button label is prefixed with a colored circle that mirrors the screenshot:
#    🔵 blue  = general / info / auth / navigation
#    🔴 red   = playback / primary action / danger / back
#    🟢 green = modifiers & settings (seek, speed, mode, loop, shuffle)
# ─────────────────────────────────────────────────────────────────────────────
BLUE = "🔵"
RED = "🔴"
GREEN = "🟢"


def btn(label: str, color: str) -> str:
    """Prefix a button label with its themed color circle."""
    return f"{color} {label}"


COLORS = {
    "saffron": "#FF6600",
    "gold":    "#FFD700",
    "green":   "#009246",
    "red":     "#CE2B37",
    "white":   "#FFFFFF",
    "dark":    "#1A0500",
}

# Emoji shortcuts
E = {
    "play":    "▶️",
    "pause":   "⏸",
    "skip":    "⏭",
    "stop":    "⏹",
    "loop":    "🔁",
    "shuffle": "🔀",
    "vol_up":  "🔊",
    "vol_dn":  "🔉",
    "mute":    "🔇",
    "lyrics":  "🎵",
    "queue":   "📋",
    "search":  "🔍",
    "owner":   "♛",
    "group":   "🏛",
    "user":    "🙋",
    "bot":     "🎶",
    "error":   "❌",
    "ok":      "✅",
    "warn":    "⚠️",
    "info":    "ℹ️",
    "fire":    "🔥",
    "star":    "⭐",
    "crown":   "👑",
}

# Common messages
STRINGS = {
    "error_generic":    "Something went wrong 🌸",
    "not_in_vc":       "Voice chat band hai, pehle VC kholo 📢",
    "no_song":         "Song nahi mili 🌸",
    "queue_empty":     "Queue empty hai 🎵",
    "nothing_playing": "Kuch nahi chal raha abhi ❌",
    "too_long":        "Song bahut lamba hai! Max {max} allowed ⏱",
    "banned":          "Aap banned hain is bot se 🚫",
    "admin_only":      "Sirf admins ya authorized users use kar sakte hain ⚠️",
}
