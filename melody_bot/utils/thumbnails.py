"""
🖼️ Thumbnail generator — 1280×720 play card with Modi-Meloni theme
"""
import io
import os
import asyncio
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
FONTS = os.path.join(ASSETS, "fonts")


def _get_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(FONTS, name)
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


async def _fetch_image(url: str) -> Image.Image | None:
    """Download an image from URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        pass
    return None


def _circle_crop(img: Image.Image, size: int) -> Image.Image:
    """Crop image to circle."""
    img = img.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(img, (0, 0), mask)
    return output


async def make_thumbnail(
    song_title: str,
    artist: str,
    duration: str,
    requester_name: str,
    group_name: str,
    owner_name: str,
    yt_thumbnail_url: str,
    requester_dp_url: str = None,
    bot_dp_url: str = None,
) -> str:
    """
    Generate a 1280×720 play card thumbnail.
    Returns path to saved image file.
    """
    W, H = 1280, 720

    # ── Background ──────────────────────────────────────────────────────────
    bg_path = os.path.join(ASSETS, "bg_main.png")
    if os.path.exists(bg_path):
        bg = Image.open(bg_path).convert("RGBA").resize((W, H))
    else:
        bg = Image.new("RGBA", (W, H), (26, 5, 0, 255))

    # Dark overlay
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 140))
    bg = Image.alpha_composite(bg, overlay)

    draw = ImageDraw.Draw(bg)

    # ── Fonts ────────────────────────────────────────────────────────────────
    font_bold_lg = _get_font("Poppins-Bold.ttf", 46)
    font_bold_md = _get_font("Poppins-Bold.ttf", 28)
    font_regular = _get_font("Poppins-Regular.ttf", 22)
    font_small = _get_font("Poppins-Regular.ttf", 18)

    # ── Song cover (circle, left side) ───────────────────────────────────────
    cover = await _fetch_image(yt_thumbnail_url)
    if cover:
        cover_circle = _circle_crop(cover, 380)
        bg.paste(cover_circle, (60, 170), cover_circle)

    # ── Vertical saffron divider ──────────────────────────────────────────────
    draw.rectangle([(490, 140), (494, 580)], fill="#FF6600")

    # ── Right panel text ──────────────────────────────────────────────────────
    rx = 520  # right panel x start

    # Song title
    draw.text((rx, 160), song_title[:40], font=font_bold_lg, fill="#FFFFFF")

    # Artist
    draw.text((rx, 220), artist[:40], font=font_bold_md, fill="#FFD700")

    # Duration
    draw.text((rx, 270), f"⏱ {duration}", font=font_regular, fill="#CCCCCC")

    # Requester
    draw.text((rx, 310), f"🙋 {requester_name[:30]}", font=font_regular, fill="#FFFFFF")

    # Group name
    draw.text((rx, 345), f"🏛 {group_name[:30]}", font=font_regular, fill="#FF6600")

    # Owner alias (from env, never real name)
    draw.text((rx, 380), f"♛ {owner_name}", font=font_bold_md, fill="#FFD700")

    # ── Progress bar (saffron→gold gradient) ─────────────────────────────────
    bar_x, bar_y, bar_w, bar_h = rx, 440, 700, 12
    for i in range(bar_w):
        ratio = i / bar_w
        r = int(255 * (1 - ratio) + 255 * ratio)
        g = int(102 * (1 - ratio) + 215 * ratio)
        b = int(0 * (1 - ratio) + 0 * ratio)
        draw.rectangle([(bar_x + i, bar_y), (bar_x + i, bar_y + bar_h)], fill=(r, g, b))

    # Bar outline
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], outline="#FF6600", width=1)

    # ── Requester DP ──────────────────────────────────────────────────────────
    if requester_dp_url:
        dp = await _fetch_image(requester_dp_url)
        if dp:
            dp_circle = _circle_crop(dp, 70)
            bg.paste(dp_circle, (rx, 580), dp_circle)

    # ── Bot DP ────────────────────────────────────────────────────────────────
    if bot_dp_url:
        bdp = await _fetch_image(bot_dp_url)
        if bdp:
            bdp_circle = _circle_crop(bdp, 70)
            bg.paste(bdp_circle, (rx + bar_w - 70, 580), bdp_circle)

    # ── Watermark ─────────────────────────────────────────────────────────────
    watermark = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wm_draw = ImageDraw.Draw(watermark)
    wm_draw.text((W // 2 - 80, H - 50), "🎶 Melody", font=font_bold_md, fill=(255, 215, 0, 60))
    bg = Image.alpha_composite(bg, watermark)

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path = f"/tmp/melody_thumb_{id(song_title)}.png"
    bg.convert("RGB").save(out_path, "PNG")
    return out_path
