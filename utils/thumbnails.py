"""
🖼️ Thumbnail generator — full-screen "now playing" card

DESIGN (v2 — full-bleed cover + spoiler + requester DP):
  • Background = the song's own cover art, SHARP (not blurred), scaled and
    cropped to fill the entire 1280×720 canvas edge-to-edge — this is what
    makes the card read as a full-screen photo of the song instead of a
    small framed thumbnail with dead space around it. Only a bottom
    gradient is added, purely so the text stays legible over any artwork.
  • The requesting user's profile photo is shown large and prominently
    (not a small icon) at the bottom-left next to their name, since that's
    the "played by" identity that matters most to the group.
  • The bot's own DP appears as a small badge, secondary to the requester.
  • Sent from play.py with Telegram's native `has_spoiler=True` so the
    photo is blurred-until-tapped in the chat itself (Telegram's own
    spoiler mechanic), on top of this full-screen artwork.
"""
import io
import os
import time
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
FONTS = os.path.join(ASSETS, "fonts")

# Bot's own DP rarely changes during a run — fetch it once and reuse.
_bot_dp_cache: dict = {"path": None, "tried": False}


def _get_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(FONTS, name)
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


async def _fetch_image_from_url(url: str) -> "Image.Image | None":
    """Download an image from a remote URL (e.g. YouTube thumbnail)."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        pass
    return None


def _load_image_any(source: str) -> "Image.Image | None":
    """Open an image from a local file path (used for downloaded DPs)."""
    try:
        if source and os.path.exists(source):
            return Image.open(source).convert("RGBA")
    except Exception:
        pass
    return None


async def fetch_dp(client, user_id: int) -> "str | None":
    """
    Download a user's (or the bot's) current profile photo to a local file
    and return the path, or None if they have no photo / it fails.
    Pyrogram doesn't expose a direct CDN URL for profile photos — they must
    be downloaded through the client.
    """
    try:
        photos = await client.get_profile_photos(user_id, limit=1)
        if not photos or not photos[0]:
            return None
        photo = photos[0]
        dest = f"/tmp/melody_dp_{user_id}_{int(time.time() * 1000)}.jpg"
        path = await client.download_media(photo.file_id, file_name=dest)
        return path
    except Exception:
        return None


async def get_bot_dp(client) -> "str | None":
    """Cached bot profile-photo path — fetched once per process lifetime."""
    if _bot_dp_cache["tried"]:
        return _bot_dp_cache["path"]
    _bot_dp_cache["tried"] = True
    try:
        me = await client.get_me()
        path = await fetch_dp(client, me.id)
        _bot_dp_cache["path"] = path
        return path
    except Exception:
        return None


def _circle_crop(img: "Image.Image", size: int, ring_color=None, ring_width: int = 0) -> "Image.Image":
    """Crop image to a circle, optionally with a colored ring border."""
    img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(img, (0, 0), mask)

    if ring_color and ring_width > 0:
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.paste(output, (0, 0), output)
        ring_draw = ImageDraw.Draw(canvas)
        ring_draw.ellipse(
            (ring_width // 2, ring_width // 2, size - ring_width // 2, size - ring_width // 2),
            outline=ring_color, width=ring_width,
        )
        return canvas
    return output


def _cover_fill_background(cover: "Image.Image", w: int, h: int) -> "Image.Image":
    """Scale+crop `cover` to fill a w×h canvas (like CSS `background-size: cover`)."""
    src_w, src_h = cover.size
    scale = max(w / src_w, h / src_h)
    new_w, new_h = int(src_w * scale) + 1, int(src_h * scale) + 1
    resized = cover.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    return resized.crop((left, top, left + w, top + h))


def _placeholder_gradient(w: int, h: int) -> "Image.Image":
    """Fallback backdrop if the YouTube thumbnail can't be fetched."""
    bg = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    draw = ImageDraw.Draw(bg)
    for y in range(h):
        ratio = y / h
        r = int(30 + 20 * ratio)
        g = int(10 + 5 * ratio)
        b = int(40 + 30 * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
    return bg


def _initials_avatar(name: str, size: int, color: str) -> "Image.Image":
    img = Image.new("RGBA", (size, size), color)
    d = ImageDraw.Draw(img)
    letter = (name or "?").strip()[:1].upper() or "?"
    f = _get_font("Poppins-Bold.ttf", int(size * 0.45))
    bbox = d.textbbox((0, 0), letter, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), letter, font=f, fill="#FFFFFF")
    return img


async def make_thumbnail(
    song_title: str,
    artist: str,
    duration: str,
    requester_name: str,
    group_name: str,
    owner_name: str,
    yt_thumbnail_url: str,
    requester_dp_path: str = None,
    bot_dp_path: str = None,
) -> str:
    """
    Generate a 1280×720 full-screen "now playing" card: the cover art fills
    the whole frame edge-to-edge (no blur, no side panel), with a bottom
    gradient carrying the song info and a large, prominent requester avatar.

    `requester_dp_path` / `bot_dp_path` are LOCAL file paths (already
    downloaded via fetch_dp()/get_bot_dp()) — not remote URLs.
    Meant to be sent with Telegram's native `has_spoiler=True` so the chat
    itself blurs it until tapped, on top of this full-bleed artwork.
    Returns the path to the saved PNG.
    """
    W, H = 1280, 720

    cover = await _fetch_image_from_url(yt_thumbnail_url)

    # ── Full-screen sharp cover art — fills the ENTIRE canvas edge-to-edge ──
    if cover:
        bg = _cover_fill_background(cover, W, H).convert("RGB")
        # Very slight enhancement so YouTube's compressed thumbnails pop,
        # without blurring or darkening the whole image like the old design.
        bg = ImageEnhance.Contrast(bg).enhance(1.06)
        bg = ImageEnhance.Color(bg).enhance(1.1)
        bg = bg.convert("RGBA")
    else:
        bg = _placeholder_gradient(W, H)

    # Bottom gradient only (not a full dark overlay) — keeps the artwork
    # full-screen and bright, just darkens enough for the text to sit on.
    gradient = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(gradient)
    fade_h = 340
    for y in range(fade_h):
        alpha = int(210 * (y / fade_h) ** 1.6)
        grad_draw.line([(0, H - fade_h + y), (W, H - fade_h + y)], fill=(0, 0, 0, alpha))
    # Slim top fade too, so the caption text Telegram overlays never
    # collides invisibly with a bright sky/white background.
    for y in range(90):
        alpha = int(120 * (1 - y / 90))
        grad_draw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    bg = Image.alpha_composite(bg, gradient)

    draw = ImageDraw.Draw(bg)

    # ── Fonts ────────────────────────────────────────────────────────────────
    font_bold_lg = _get_font("Poppins-Bold.ttf", 48)
    font_bold_md = _get_font("Poppins-Bold.ttf", 26)
    font_regular = _get_font("Poppins-Regular.ttf", 22)
    font_small = _get_font("Poppins-Regular.ttf", 18)

    pad = 56

    # ── Song info, bottom-left over the gradient ───────────────────────────
    text_y = H - 300
    draw.text((pad, text_y), song_title[:42], font=font_bold_lg, fill="#FFFFFF")
    draw.text((pad, text_y + 60), artist[:40], font=font_bold_md, fill="#FFD700")
    draw.text((pad, text_y + 100), f"⏱ {duration}   🏛 {group_name[:28]}", font=font_regular, fill="#EEEEEE")

    # ── Progress bar (saffron → gold gradient) ─────────────────────────────
    bar_x, bar_y, bar_w, bar_h = pad, text_y + 145, W - pad * 2, 10
    for i in range(bar_w):
        ratio = i / bar_w
        r = 255
        g = int(102 * (1 - ratio) + 215 * ratio)
        b = 0
        draw.rectangle([(bar_x + i, bar_y), (bar_x + i, bar_y + bar_h)], fill=(r, g, b))
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], outline="#FFD700", width=1)

    # ── Requester identity — LARGE and prominent (the main ask: "requester
    # ka DP dikhe"), bot DP shown small as a secondary badge on top of it ───
    row_y = bar_y + 34
    requester_size = 108

    bot_img = _load_image_any(bot_dp_path) if bot_dp_path else None
    user_img = _load_image_any(requester_dp_path) if requester_dp_path else None

    user_circle = _circle_crop(
        user_img if user_img else _initials_avatar(requester_name, requester_size, "#8B0000"),
        requester_size, ring_color="#FFD700", ring_width=5,
    )
    bg.paste(user_circle, (pad, row_y), user_circle)

    # Small bot-DP badge overlapping the bottom-right of the big requester
    # avatar (secondary, like a "played via" mark).
    bot_badge_size = 46
    bot_circle = _circle_crop(
        bot_img if bot_img else _initials_avatar("Melody", bot_badge_size, "#B8860B"),
        bot_badge_size, ring_color="#FFFFFF", ring_width=3,
    )
    bg.paste(
        bot_circle,
        (pad + requester_size - bot_badge_size + 8, row_y + requester_size - bot_badge_size + 8),
        bot_circle,
    )

    label_x = pad + requester_size + 24
    draw.text((label_x, row_y + 14), "🙋 Requested by", font=font_small, fill="#CCCCCC")
    draw.text((label_x, row_y + 40), requester_name[:24], font=font_bold_md, fill="#FFFFFF")
    draw.text((label_x, row_y + 76), f"🤖 via Melody · ♛ {owner_name[:18]}", font=font_small, fill="#FFD700")

    # ── Watermark ─────────────────────────────────────────────────────────
    wm_draw = ImageDraw.Draw(bg)
    wm_draw.text((W - 190, 24), "🎶 Melody", font=font_bold_md, fill=(255, 255, 255, 170))

    # ── Save ──────────────────────────────────────────────────────────────
    out_path = f"/tmp/melody_thumb_{int(time.time() * 1000)}.png"
    bg.convert("RGB").save(out_path, "PNG")
    return out_path
