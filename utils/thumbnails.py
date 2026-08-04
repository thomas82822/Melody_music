"""
🖼️ Thumbnail generator — Telegram-style blurred now-playing card

DESIGN (requirement #1 — "dimag laga ke" blurred card):
  • Background = the song's own cover art, blown up to fill the full
    1280×720 canvas and heavily Gaussian-blurred + darkened — exactly the
    blurred-placeholder look Telegram itself uses for photos/videos while
    they load. This replaces the old flat/solid-color background and means
    every card is uniquely themed around the song being played instead of
    a generic static backdrop.
  • Foreground = a crisp, un-blurred circular crop of the SAME cover art,
    framed with a soft gold ring, so the blur reads as "this photo, out of
    focus" rather than a mismatched decoration.
  • A "played by" avatar cluster at the bottom overlaps the bot's profile
    photo and the requesting user's profile photo (like Telegram's voice
    chat participant avatars), with a small connecting music-note badge —
    this is what satisfies "cover art + bot ka dp + requester ka dp".
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
    Generate a 1280×720 Telegram-style blurred now-playing card.
    `requester_dp_path` / `bot_dp_path` are LOCAL file paths (already
    downloaded via fetch_dp()/get_bot_dp()) — not remote URLs.
    Returns the path to the saved PNG.
    """
    W, H = 1280, 720

    cover = await _fetch_image_from_url(yt_thumbnail_url)

    # ── Blurred Telegram-style backdrop ────────────────────────────────────
    if cover:
        bg = _cover_fill_background(cover, W, H).convert("RGB")
        bg = bg.filter(ImageFilter.GaussianBlur(radius=38))
        bg = ImageEnhance.Brightness(bg).enhance(0.45)
        bg = ImageEnhance.Color(bg).enhance(1.15)
        bg = bg.convert("RGBA")
    else:
        bg = _placeholder_gradient(W, H)

    # Extra dark vignette so text stays readable over any cover art
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([(0, 0), (W, H)], fill=(0, 0, 0, 90))
    ov_draw.rectangle([(0, H - 220), (W, H)], fill=(0, 0, 0, 70))
    bg = Image.alpha_composite(bg, overlay)

    draw = ImageDraw.Draw(bg)

    # ── Fonts ────────────────────────────────────────────────────────────────
    font_bold_lg = _get_font("Poppins-Bold.ttf", 46)
    font_bold_md = _get_font("Poppins-Bold.ttf", 26)
    font_regular = _get_font("Poppins-Regular.ttf", 22)
    font_small = _get_font("Poppins-Regular.ttf", 17)

    # ── Sharp circular cover art (the "in-focus" version of the blur) ─────────
    if cover:
        cover_circle = _circle_crop(cover, 340, ring_color="#FFD700", ring_width=6)
        bg.paste(cover_circle, (70, 190), cover_circle)

    # ── Divider ─────────────────────────────────────────────────────────────
    draw.rectangle([(455, 150), (459, 560)], fill=(255, 215, 0, 160))

    # ── Right panel text ────────────────────────────────────────────────────
    rx = 490

    draw.text((rx, 150), song_title[:38], font=font_bold_lg, fill="#FFFFFF")
    draw.text((rx, 212), artist[:40], font=font_bold_md, fill="#FFD700")
    draw.text((rx, 258), f"⏱ {duration}", font=font_regular, fill="#DDDDDD")
    draw.text((rx, 296), f"🏛 {group_name[:32]}", font=font_regular, fill="#FF6600")

    # ── Progress bar (saffron → gold gradient) ─────────────────────────────
    bar_x, bar_y, bar_w, bar_h = rx, 340, 700, 10
    for i in range(bar_w):
        ratio = i / bar_w
        r = int(255 * (1 - ratio) + 255 * ratio)
        g = int(102 * (1 - ratio) + 215 * ratio)
        b = int(0 * (1 - ratio) + 0 * ratio)
        draw.rectangle([(bar_x + i, bar_y), (bar_x + i, bar_y + bar_h)], fill=(r, g, b))
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], outline="#FFD700", width=1)

    # ── "Played by" avatar cluster: bot DP + requester DP, overlapping ──────
    # Telegram-VC style: two overlapping circular avatars with a small
    # connecting music-note badge, plus the requester's name/handle.
    cluster_y = 380
    avatar_size = 78

    bot_img = _load_image_any(bot_dp_path) if bot_dp_path else None
    user_img = _load_image_any(requester_dp_path) if requester_dp_path else None

    def _initials_avatar(name: str, size: int, color: str) -> "Image.Image":
        img = Image.new("RGBA", (size, size), color)
        d = ImageDraw.Draw(img)
        letter = (name or "?").strip()[:1].upper() or "?"
        f = _get_font("Poppins-Bold.ttf", int(size * 0.45))
        bbox = d.textbbox((0, 0), letter, font=f)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), letter, font=f, fill="#FFFFFF")
        return img

    bot_circle = _circle_crop(
        bot_img if bot_img else _initials_avatar("Melody", avatar_size, "#B8860B"),
        avatar_size, ring_color="#FFFFFF", ring_width=4,
    )
    user_circle = _circle_crop(
        user_img if user_img else _initials_avatar(requester_name, avatar_size, "#8B0000"),
        avatar_size, ring_color="#FFFFFF", ring_width=4,
    )

    bg.paste(bot_circle, (rx, cluster_y), bot_circle)
    bg.paste(user_circle, (rx + avatar_size - 26, cluster_y), user_circle)

    # Small connecting "played" badge between the two avatars
    badge_size = 30
    badge = Image.new("RGBA", (badge_size, badge_size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    bd.ellipse((0, 0, badge_size, badge_size), fill="#25D366", outline="#FFFFFF", width=2)
    bf = _get_font("Poppins-Bold.ttf", 16)
    bd.text((7, 5), "▶", font=bf, fill="#FFFFFF")
    bg.paste(badge, (rx + avatar_size - 26 + avatar_size - 16, cluster_y + avatar_size - 16), badge)

    label_x = rx + (avatar_size * 2) + 20
    draw.text((label_x, cluster_y + 6), "🤖 Melody", font=font_small, fill="#FFD700")
    draw.text((label_x, cluster_y + 30), f"🙋 {requester_name[:22]}", font=font_small, fill="#FFFFFF")
    draw.text((label_x, cluster_y + 54), f"♛ {owner_name}", font=font_small, fill="#CCCCCC")

    # ── Watermark ─────────────────────────────────────────────────────────
    wm_draw = ImageDraw.Draw(bg)
    wm_draw.text((W - 190, H - 40), "🎶 Melody", font=font_bold_md, fill=(255, 215, 0, 90))

    # ── Save ──────────────────────────────────────────────────────────────
    out_path = f"/tmp/melody_thumb_{int(time.time() * 1000)}.png"
    bg.convert("RGB").save(out_path, "PNG")
    return out_path
