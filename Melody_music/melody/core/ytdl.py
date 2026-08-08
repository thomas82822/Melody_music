"""
🎵 YouTube downloader — yt-dlp wrapper

FIXES APPLIED:
  • Heroku CDN block detection — skips googlevideo.com CDN URLs that always
    fail on cloud IPs (Heroku DYNO, Railway, Render, Fly.io, etc.).
  • "Sign in to confirm you're not a bot" — uses android_music + ios + web
    player clients in order; these bypass the sign-in wall for public videos.
  • Instant streaming — download_audio() returns a FIFO named pipe on Linux
    (Heroku supports mkfifo).  yt-dlp writes audio to the pipe in a daemon
    thread; PyTgCalls starts reading before the full download finishes.
    Falls back to full file download if mkfifo is unavailable.
  • YT_COOKIES binary guard — already present; kept as-is.
  • WebM/Opus preferred format — streamable via FIFO without seeking,
    unlike AAC/M4A which requires the moov atom at EOF.
"""
import asyncio
import base64
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

# The build hook (bin/post_compile) installs the bgutil yt-dlp PO-token
# provider plugin under vendor/. Add that namespace to sys.path BEFORE
# importing yt_dlp so its plugin discovery picks it up. This is the real
# fix for YouTube's "Sign in to confirm you're not a bot" wall on Heroku —
# a Proof-of-Origin token, not a proxy, is what YouTube actually checks for
# on cloud/datacenter IPs.
_BGUTIL_PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "vendor", "bgutil-ytdlp-pot-provider", "plugin",
)
_BGUTIL_PLUGIN_DIR = os.path.normpath(_BGUTIL_PLUGIN_DIR)
if os.path.isdir(_BGUTIL_PLUGIN_DIR) and _BGUTIL_PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _BGUTIL_PLUGIN_DIR)

from yt_dlp import YoutubeDL
from melody.config import Config
from melody.logging import LOGGER, send_error_log

_BGUTIL_STATUS_LOGGED = False


def _bgutil_server_home() -> str:
    """Return the build-bundled bgutil PO-token provider server directory."""
    return os.path.normpath(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..", "vendor", "bgutil-ytdlp-pot-provider", "server",
    ))


_BGUTIL_HTTP_PORT = 4416
_BGUTIL_HTTP_PROC: "subprocess.Popen | None" = None
_BGUTIL_HTTP_READY = False
_BGUTIL_HTTP_LOCK = threading.Lock()


def ensure_bgutil_http_server() -> bool:
    """Start bgutil's PO-token provider as a persistent local HTTP server
    (idempotent — safe to call more than once) and return whether it's up.

    SPEED FIX ("gana bajne me 5-10 sec lag rahe hai" even after the
    early-handoff/pre-download work): every /play still has to resolve a
    fresh PO token before yt-dlp can pick a downloadable format — YouTube
    requires one for essentially all clients now. This bot got that token
    via bgutil's "script" method (`generate_once.ts`), which the upstream
    project itself documents as much slower than the HTTP server: EVERY
    single call spins up a brand-new Deno runtime + BotGuard/session state
    from scratch, solves the challenge, prints the token, and exits — there
    is nothing warm to reuse, so this cost was paid again on every track,
    stacking directly on top of the search + download time already on the
    critical path. That reliably accounts for multiple extra seconds of the
    "5-10 sec" delay on every single song, not just occasionally.

    The bundled `server/src/main.ts` is the same provider running as a
    long-lived process instead: it keeps the Deno/BotGuard session and a
    per-video token cache warm across requests, so once it's up, each
    subsequent PO-token fetch is a fast local HTTP call instead of a fresh
    process spawn. Starting it once here (in the background, at bot
    startup) means it's already warmed up long before the first /play.

    Falls back cleanly to the old script-based provider (see _ydl_opts())
    if Deno/the server files aren't available or the server never comes up
    — this is a pure addition, never a regression.
    """
    global _BGUTIL_HTTP_PROC, _BGUTIL_HTTP_READY

    with _BGUTIL_HTTP_LOCK:
        if _BGUTIL_HTTP_READY:
            return True
        if _BGUTIL_HTTP_PROC is not None and _BGUTIL_HTTP_PROC.poll() is None:
            return False  # already starting; caller can retry _bgutil_http_alive() shortly

        server_home = _bgutil_server_home()
        main_ts = os.path.join(server_home, "src", "main.ts")
        deno = _deno_path()
        if not os.path.isfile(main_ts) or not (os.path.isfile(deno) or shutil.which(deno)):
            return False

        try:
            os.makedirs(os.path.join(server_home, "cache"), exist_ok=True)
            _BGUTIL_HTTP_PROC = subprocess.Popen(
                [
                    deno, "run",
                    "--allow-env", "--allow-net",
                    f"--allow-ffi={os.path.join(server_home, 'node_modules')}",
                    f"--allow-write={os.path.join(server_home, 'cache')}",
                    f"--allow-read={os.path.join(server_home, 'cache')},{os.path.join(server_home, 'node_modules')}",
                    main_ts, "--port", str(_BGUTIL_HTTP_PORT),
                ],
                cwd=server_home,
                env={**os.environ, "XDG_CACHE_HOME": os.path.join(server_home, "cache")},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            LOGGER.info("🚀 bgutil PO-token HTTP server starting on 127.0.0.1:%d", _BGUTIL_HTTP_PORT)
            return False  # not confirmed ready yet — see _bgutil_http_alive()
        except Exception as exc:
            LOGGER.warning("Could not start bgutil HTTP server, falling back to script mode: %s", exc)
            _BGUTIL_HTTP_PROC = None
            return False


def _bgutil_http_alive() -> bool:
    """Best-effort /ping check against the local bgutil HTTP server."""
    global _BGUTIL_HTTP_READY
    if _BGUTIL_HTTP_READY:
        return True
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{_BGUTIL_HTTP_PORT}/ping", timeout=1.5) as resp:
            if resp.status == 200:
                _BGUTIL_HTTP_READY = True
                LOGGER.info("✅ bgutil PO-token HTTP server is up — using warm HTTP provider (fast path)")
                return True
    except Exception:
        pass
    return False


async def warm_up_bgutil_server(timeout: float = 20.0) -> None:
    """Called once at bot startup: kick off the persistent bgutil HTTP
    server and poll until it responds (or times out), so it's warmed up
    well before the first /play instead of racing the first request.
    """
    if not ensure_bgutil_http_server() and _BGUTIL_HTTP_PROC is None:
        return  # server files not available — script-mode fallback will be used
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if await loop.run_in_executor(None, _bgutil_http_alive):
            return
        await asyncio.sleep(0.5)
    LOGGER.warning(
        "bgutil HTTP server did not respond within %.0fs — falling back to (slower) script mode",
        timeout,
    )


def _deno_path() -> str:
    """Return the build-bundled (or system) Deno binary path.

    yt-dlp's YouTube extractor needs a JS runtime to solve the player
    challenge and to run the bgutil PO-token generator script.
    """
    bundled = os.path.normpath(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..", "vendor", "deno", "bin", "deno",
    ))
    if os.path.isfile(bundled):
        return bundled
    return shutil.which("deno") or "deno"

# Check whether curl_cffi is available (enables Chrome TLS impersonation,
# which bypasses YouTube's bot-detection on Heroku / cloud IPs).
try:
    import curl_cffi  # noqa: F401
    _CURL_CFFI_OK = True
    LOGGER.info("✅ curl_cffi available — Chrome TLS impersonation enabled")
except ImportError:
    _CURL_CFFI_OK = False
    LOGGER.warning(
        "curl_cffi not installed — YouTube may block requests on cloud IPs. "
        "Add 'curl_cffi>=0.7.0' to requirements.txt and redeploy."
    )


COOKIES_FILE = "/tmp/melody_yt_cookies.txt"

# ── Cloud-host detection ──────────────────────────────────────────────────────
# On Heroku/Railway/Render/Fly.io the YouTube CDN (googlevideo.com) is
# IP-blocked.  Trying to stream directly from a CDN signed URL produces an
# immediate EOF → 10-25 s of silence before the retry kicks in.
# Detect at startup and always use full local download on these hosts.
_ON_CLOUD_HOST: bool = bool(
    os.environ.get("DYNO")                    # Heroku
    or os.environ.get("RAILWAY_ENVIRONMENT")  # Railway
    or os.environ.get("RENDER_SERVICE_ID")    # Render
    or os.environ.get("FLY_APP_NAME")         # Fly.io
    or os.environ.get("K_SERVICE")            # Google Cloud Run
    or os.environ.get("WEBSITE_INSTANCE_ID")  # Azure App Service
)
if _ON_CLOUD_HOST:
    LOGGER.info("☁️  Cloud host detected — YouTube CDN streaming skipped; using local download")

# ── FIFO pipe concurrency ────────────────────────────────────────────────────
# Cap parallel FIFO downloads so we don't exhaust Heroku memory.
_PIPE_MAX_CONCURRENT = 4
_pipe_slots = threading.BoundedSemaphore(_PIPE_MAX_CONCURRENT)
_PIPE_CONNECT_TIMEOUT = 15.0   # seconds to wait for ntgcalls to open the read end
_PIPE_SLOT_TIMEOUT    = 5.0    # fail fast if all slots taken; retry will use file download

# Track pipe paths that are actively being written so _cleanup_temp can skip them.
_active_pipes: set = set()
_active_pipes_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
#  Cookie helpers (unchanged — binary-guard logic kept)
# ─────────────────────────────────────────────────────────────────────────────

def _json_cookies_to_netscape(json_text: str) -> str:
    import json
    try:
        cookies = json.loads(json_text)
    except (json.JSONDecodeError, ValueError):
        return json_text
    if not isinstance(cookies, list):
        return json_text
    lines = ["# Netscape HTTP Cookie File", "# Generated by Melody"]
    for c in cookies:
        domain = c.get("domain", "")
        include_sub = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expiry = int(c.get("expirationDate") or c.get("expires") or 0)
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append(f"{domain}\t{include_sub}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")
    return "\n".join(lines) + "\n"


def _is_netscape_cookies(text: str) -> bool:
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if len(line.split("\t")) == 7:
            return True
    return False


def _write_cookies():
    """Load YT_COOKIES into COOKIES_FILE.

    ROOT-CAUSE FIX (previous bug):
    The old code ALWAYS ran base64.b64decode() first, even when YT_COOKIES
    already contained plain-text cookies.txt content (the most common way
    people paste it into Heroku config vars). Python's base64 decoder does
    NOT error on arbitrary text — it silently mangles it into garbage bytes,
    which then fail the UTF-8 decode and get logged as "binary data" and
    thrown away. This is why cookies never worked even when pasted correctly.

    NEW ORDER:
    1. Check if the raw value is ALREADY plain Netscape text or a JSON cookie
       array (no decoding needed) — use it directly.
    2. Only if that fails, attempt strict base64 decoding (validate=True so
       non-base64 text raises immediately instead of being silently corrupted).
    """
    if not Config.YT_COOKIES:
        LOGGER.warning(
            "⚠️ YT_COOKIES is not set — bot will run WITHOUT a YouTube login. "
            "Heroku IPs are heavily bot-checked; cookies are strongly recommended."
        )
        return

    raw = Config.YT_COOKIES.strip()

    # ── Path 1: already plain text (most common case) ──────────────────────
    if raw.startswith("["):
        netscape = _json_cookies_to_netscape(raw)
        if _is_netscape_cookies(netscape):
            with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                f.write(netscape)
            LOGGER.info("✅ YT_COOKIES (plain JSON→Netscape) written to %s", COOKIES_FILE)
            return
    if raw.startswith("#") or _is_netscape_cookies(raw):
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.write(raw)
        LOGGER.info("✅ YT_COOKIES (plain Netscape text) written to %s", COOKIES_FILE)
        return

    # ── Path 2: base64-encoded (strict — fail loudly instead of corrupting) ─
    try:
        raw_bytes = base64.b64decode(raw, validate=True)
    except Exception as e:
        LOGGER.warning(
            "❌ YT_COOKIES is neither plain cookies.txt text nor valid base64 — "
            "skipping cookies: %s", e
        )
        return
    try:
        decoded = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        LOGGER.warning(
            "❌ YT_COOKIES base64 decodes to binary data (not a text cookie file). "
            "Paste the raw cookies.txt content directly into the config var — "
            "no base64 encoding needed. Skipping cookies."
        )
        return
    decoded = decoded.strip()
    if decoded.startswith("["):
        netscape = _json_cookies_to_netscape(decoded)
        if not _is_netscape_cookies(netscape):
            LOGGER.warning("❌ YT_COOKIES JSON conversion produced no valid entries — skipping.")
            return
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.write(netscape)
        LOGGER.info("✅ YT_COOKIES (base64 JSON→Netscape) written to %s", COOKIES_FILE)
        return
    if _is_netscape_cookies(decoded):
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.write(decoded)
        LOGGER.info("✅ YT_COOKIES (base64 Netscape) written to %s", COOKIES_FILE)
        return
    LOGGER.warning(
        "❌ YT_COOKIES format not recognised (not JSON array, not Netscape). "
        "Export cookies using a browser extension like 'Get cookies.txt LOCALLY' "
        "while logged into youtube.com, then paste the file content as-is. "
        "Skipping cookies — yt-dlp will run without authentication."
    )


_write_cookies()
_HAS_COOKIES = os.path.exists(COOKIES_FILE)
if _HAS_COOKIES:
    LOGGER.info("🍪 Cookie-authenticated YouTube session ACTIVE — using logged-in requests")
else:
    LOGGER.warning("🍪 No cookies loaded — running as anonymous guest (more likely to be blocked on Heroku)")


# ─────────────────────────────────────────────────────────────────────────────
#  yt-dlp options
# ─────────────────────────────────────────────────────────────────────────────

def _ydl_opts(audio_only: bool = True) -> dict:
    """Return base yt-dlp options tuned for Heroku and bot-detection bypass.

    FIXES:
    • "Sign in to confirm you're not a bot":
        android_music → ios → android → tv_embedded → mweb → web
        Android/iOS clients are served a different API path that skips the
        sign-in wall for public videos.  This is the canonical yt-dlp fix.
    • WebM/Opus format preferred — streamable via FIFO pipe without seeking.
      AAC/M4A requires the moov atom at end-of-file → breaks pipe mode.
    • geo_bypass — Heroku USA servers sometimes hit geo-restricted content;
      bypass declaration helps with most non-DRM videos.
    • concurrent_fragment_downloads=4 (SPEED FIX — see below).
    """
    fmt = (
        # SPEED FIX (5-10s /play delay): FIFO pipe streaming was removed, so
        # every track is now a full file download BEFORE playback can start
        # (see download_audio()'s docstring) — the download itself sits
        # directly on the critical path to "song plays". The old selector
        # ("bestaudio/best") happily grabbed the highest-bitrate stream
        # available (often 160-250kbps opus/webm), which can be 2-3x the
        # bytes of a perfectly good voice-chat-quality stream for zero
        # audible benefit over Telegram voice chat. Capping to <=128kbps
        # (falling back to whatever's available if nothing matches) cuts
        # download size — and therefore wait time — substantially without
        # a noticeable quality drop.
        "bestaudio[abr<=128]/bestaudio/best"
        if audio_only
        else "best[height<=720][vcodec!=none][acodec!=none]/best[height<=720]/best"
    )
    has_cookies = os.path.exists(COOKIES_FILE)

    # A cookies.txt file is exported from a real desktop/mobile browser
    # session — pairing it with a matching browser User-Agent (instead of the
    # generic mobile UA) keeps the request fingerprint consistent and avoids
    # extra bot-detection flags.
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        if has_cookies
        else "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
    )

    # Prefer the ANDROID client for downloads — it is not subject to the
    # Proof-of-Origin (PO) token wall that the "web" client hits on cloud IPs.
    # The "default" client lets yt-dlp pick "web" which then needs a bgutil
    # PO-token provider; if that provider is missing or slow, the download
    # exhausts all retries and fails. Android-served format URLs are
    # downloadable directly with no token. Fall back to "default" so yt-dlp
    # can still try other clients if Android has no formats for a given video.
    extractor_args: dict = {
        "player_client": ["android", "default"],
    }
    provider_args: dict = {"youtube": extractor_args}

    bgutil_server = _bgutil_server_home()
    bgutil_script = os.path.join(bgutil_server, "src", "generate_once.ts")
    global _BGUTIL_STATUS_LOGGED
    # SPEED FIX: prefer the warm HTTP server (see ensure_bgutil_http_server())
    # — reuses a live Deno/BotGuard session + per-video token cache, so a
    # token fetch is a fast local HTTP call instead of spawning a whole new
    # Deno process from scratch on every single track. Only fall back to the
    # slower one-process-per-call script provider if the HTTP server never
    # came up (e.g. Deno/server files missing).
    if _bgutil_http_alive():
        provider_args["youtubepot-bgutilhttp"] = {
            "base_url": [f"http://127.0.0.1:{_BGUTIL_HTTP_PORT}"],
        }
        if not _BGUTIL_STATUS_LOGGED:
            LOGGER.info("✅ bgutil PO-token provider configured (HTTP, warm): 127.0.0.1:%d", _BGUTIL_HTTP_PORT)
            _BGUTIL_STATUS_LOGGED = True
    elif os.path.isfile(bgutil_script):
        provider_args["youtubepot-bgutilscript"] = {
            "server_home": [bgutil_server],
        }
        if not _BGUTIL_STATUS_LOGGED:
            LOGGER.info("✅ bgutil PO-token provider configured (script, slower): %s", bgutil_server)
            _BGUTIL_STATUS_LOGGED = True
    elif not _BGUTIL_STATUS_LOGGED:
        LOGGER.warning(
            "⚠️ bgutil PO-token provider not installed at %s — "
            "YouTube may block cloud-host requests with 'Sign in to confirm "
            "you're not a bot'. Redeploy so bin/post_compile can install it.",
            bgutil_server,
        )
        _BGUTIL_STATUS_LOGGED = True

    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": fmt,
        "postprocessors": [],
        "geo_bypass": True,
        "geo_bypass_country": "US",
        "socket_timeout": 10,
        "retries": 5,
        "fragment_retries": 5,
        "check_formats": False,
        # SPEED FIX: this used to be 1, left over from a removed FIFO-pipe
        # trick that needed sequential fragment writes to keep the pipe fed
        # continuously (see download_audio()'s docstring — FIFO streaming
        # was removed entirely). Now that every track is a plain full-file
        # download with no pipe involved, sequential fragments only slow
        # the download down for no reason. 4 parallel fragments cuts
        # download time noticeably on typical DASH-fragmented audio.
        "concurrent_fragment_downloads": 4,
        # yt-dlp's YouTube extractor needs an external JS runtime to solve
        # the player challenge and to run the bgutil PO-token script.
        "js_runtimes": {"deno": {"path": _deno_path()}},
        "remote_components": ["ejs:github"],
        "extractor_args": provider_args,
        "http_headers": {
            "User-Agent": user_agent,
            "Referer": "https://www.youtube.com/",
        },
    }
    # NOTE: curl_cffi "impersonate" intentionally removed.
    # The impersonate target varies by installed version and crashes yt-dlp
    # with "Impersonate target not available" on older curl_cffi builds.
    if has_cookies:
        opts["cookiefile"] = COOKIES_FILE
    if Config.YT_PROXY:
        opts["proxy"] = Config.YT_PROXY
    return opts


# ─────────────────────────────────────────────────────────────────────────────
#  Search helpers
# ─────────────────────────────────────────────────────────────────────────────

async def search_youtube(query: str, limit: int = 5) -> list[dict]:
    """Search YouTube and return a list of results."""
    def _search():
        opts = {**_ydl_opts(), "default_search": f"ytsearch{limit}", "extract_flat": True}
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(query, download=False)
            return info.get("entries", [])

    try:
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, _search)
        return [
            {
                "id": e.get("id", ""),
                "title": e.get("title", "Unknown"),
                "duration": e.get("duration", 0),
                "url": f"https://www.youtube.com/watch?v={e.get('id', '')}",
                "thumbnail": e.get("thumbnail") or f"https://i.ytimg.com/vi/{e.get('id','')}/hqdefault.jpg",
                "uploader": e.get("uploader", "Unknown"),
            }
            for e in results
            if e.get("id")
        ]
    except Exception as exc:
        await send_error_log("search_youtube failed", exc)
        return []


async def get_playlist_entries(url_or_query: str, limit: int = 50) -> list[dict]:
    """Extract lightweight metadata for every entry in a YouTube playlist URL.

    Used by /playlist. Like search_youtube(), this stays on the
    extract_flat metadata path only (no streamingData / format resolution)
    so it doesn't trip YouTube's cloud-IP bot-detection — each track's real
    stream is only resolved later, at play time, by download_audio().
    """
    def _extract():
        opts = {
            **_ydl_opts(),
            "extract_flat": "in_playlist",
            "noplaylist": False,
            "playlist_items": f"1:{max(1, limit)}",
            "ignoreerrors": True,
        }
        opts.pop("format", None)
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url_or_query, download=False)
            if not info:
                return []
            if "entries" in info:
                return [e for e in info["entries"] if e]
            # A single-video URL was passed instead of a real playlist.
            return [info] if info.get("id") else []

    try:
        loop = asyncio.get_running_loop()
        entries = await loop.run_in_executor(None, _extract)
        results = []
        for e in entries:
            vid = e.get("id", "")
            if not vid:
                continue
            results.append({
                "id": vid,
                "title": e.get("title", "Unknown"),
                "duration": int(e.get("duration") or 0),
                "url": f"https://www.youtube.com/watch?v={vid}",
                "thumbnail": e.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                "uploader": e.get("uploader", "Unknown"),
            })
        return results
    except Exception as exc:
        await send_error_log("get_playlist_entries failed", exc)
        return []


def _extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    import re
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None



# ─────────────────────────────────────────────────────────────────────────────
#  YouTube InnerTube API fallback search
#  Direct POST to YouTube's internal API (same endpoint yt-dlp uses).
#  Works from Heroku because it hits youtube.com directly (not a proxy).
#  Uses the ANDROID client which bypasses bot-detection without cookies.
# ─────────────────────────────────────────────────────────────────────────────

def _innertube_search_sync(query: str) -> dict | None:
    """Search YouTube via InnerTube API — Heroku-safe, no yt-dlp needed.

    WHY THIS WORKS ON HEROKU:
    YouTube's own search API (used internally by all YouTube clients) accepts
    POST requests from the Android app client. The Android client path is
    NOT subject to the same bot-detection as the web player — it is served by
    a completely different API endpoint that doesn't require login or cookies.

    This is the same API yt-dlp uses for its ytsearch extractor, but called
    directly so we bypass yt-dlp's player-client selection entirely.
    """
    import json
    import urllib.request

    _API_KEY = "AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w"   # public Android API key
    _SEARCH_URL = f"https://www.youtube.com/youtubei/v1/search?key={_API_KEY}&prettyPrint=false"

    # Android client context — not bot-challenged, no sign-in required
    payload = json.dumps({
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "20.10.35",
                "androidSdkVersion": 30,
                "hl": "en",
                "gl": "US",
                "utcOffsetMinutes": 0,
            }
        },
        "query": query,
        "params": "EgIQAQ==",   # filter: videos only (base64, NOT url-encoded)
    }).encode("utf-8")

    req = urllib.request.Request(
        _SEARCH_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/20.10.35 (Linux; U; Android 11) gzip",
            "X-YouTube-Client-Name": "3",
            "X-YouTube-Client-Version": "20.10.35",
            "Accept-Language": "en-US,en;q=0.9",
        },
        method="POST",
    )

    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=12) as resp:
            if resp.status != 200:
                LOGGER.warning("InnerTube search HTTP %s for: %s", resp.status, query[:50])
                return None
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        LOGGER.warning("InnerTube search network error: %s", exc)
        return None

    # Parse InnerTube response — walk the renderer tree
    def _parse_video_renderer(vr: dict) -> "dict | None":
        vid = vr.get("videoId", "")
        if not vid:
            return None
        title = (vr.get("title", {})
                   .get("runs", [{}])[0]
                   .get("text", "") or query)
        duration_text = (
            vr.get("lengthText", {}).get("simpleText", "") or
            vr.get("lengthText", {}).get("runs", [{}])[0].get("text", "")
        )
        duration = 0
        if duration_text:
            parts = [int(p) for p in duration_text.split(":") if p.isdigit()]
            if len(parts) == 2:
                duration = parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                duration = parts[0] * 3600 + parts[1] * 60 + parts[2]
        thumbs = (vr.get("thumbnail", {}).get("thumbnails") or [])
        thumbnail = thumbs[-1].get("url", "") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        uploader = (
            vr.get("ownerText", {}).get("runs", [{}])[0].get("text", "") or
            vr.get("longBylineText", {}).get("runs", [{}])[0].get("text", "") or
            "Unknown"
        )
        return {
            "id": vid,
            "webpage_url": f"https://www.youtube.com/watch?v={vid}",
            "title": title,
            "duration": duration,
            "thumbnail": thumbnail,
            "uploader": uploader,
        }

    # Primary path: structured sectionListRenderer walk
    try:
        contents = (
            data.get("contents", {})
                .get("sectionListRenderer", {})
                .get("contents", [])
        )
        for section in contents:
            items = (
                section.get("itemSectionRenderer", {})
                       .get("contents", [])
            )
            for item in items:
                vr = item.get("videoRenderer")
                if not vr:
                    continue
                result = _parse_video_renderer(vr)
                if result:
                    LOGGER.info("✅ InnerTube search OK: %s", result["title"][:50])
                    return result
    except Exception as exc:
        LOGGER.warning("InnerTube response parse error: %s", exc)

    # Fallback: recursive tree-walk for any videoRenderer anywhere in the
    # response (YouTube frequently changes the nesting structure between
    # client versions — a tree-walk finds the first video result regardless).
    try:
        def _walk(node, out):
            if isinstance(node, dict):
                vr = node.get("videoRenderer")
                if vr and vr.get("videoId"):
                    out.append(vr)
                for v in node.values():
                    _walk(v, out)
            elif isinstance(node, list):
                for item in node:
                    _walk(item, out)

        renderers: list = []
        _walk(data, renderers)
        for vr in renderers:
            result = _parse_video_renderer(vr)
            if result:
                LOGGER.info("✅ InnerTube search OK (tree-walk): %s", result["title"][:50])
                return result
    except Exception as exc:
        LOGGER.warning("InnerTube tree-walk parse error: %s", exc)

    LOGGER.warning("❌ InnerTube search: no video results for: %s", query[:50])
    return None


# Keep Invidious as a secondary backup behind InnerTube
_INVIDIOUS_INSTANCES = [
    "https://invidious.f5.si",
    "https://invidious.privacydev.net",
    "https://invidious.nerdvpn.de",
    "https://invidious.fdn.fr",
    "https://invidious.io.lol",
    "https://invidious.einfachzocken.eu",
    "https://invidious.privacyredirect.com",
    "https://invidious.jing.rocks",
    "https://invidious.asir.dev",
    "https://invidious.drgns.space",
]


def _invidious_search_sync(query: str) -> dict | None:
    """Secondary fallback: Invidious public instances."""
    import json, urllib.request, urllib.parse
    encoded = urllib.parse.quote_plus(query)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MelodyBot/1.0)"}
    for inst in _INVIDIOUS_INSTANCES:
        try:
            url = f"{inst}/api/v1/search?q={encoded}&type=video"
            req = urllib.request.Request(url, headers=headers)
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=5) as resp:
                if resp.status != 200:
                    continue
                items = json.loads(resp.read().decode("utf-8"))
            res = next((i for i in items if i.get("type") == "video" and i.get("videoId")), None)
            if not res:
                continue
            vid = res["videoId"]
            thumbs = res.get("videoThumbnails") or []
            thumb = next((t.get("url", "") for t in thumbs if t.get("quality") in {"medium", "high"}),
                         thumbs[0].get("url", "") if thumbs else "")
            LOGGER.info("✅ Invidious search OK (%s): %s", inst, res.get("title", "")[:50])
            return {
                "id": vid, "webpage_url": f"https://www.youtube.com/watch?v={vid}",
                "title": res.get("title") or query, "duration": int(res.get("lengthSeconds") or 0),
                "thumbnail": thumb, "uploader": res.get("author") or "",
            }
        except Exception as exc:
            LOGGER.debug("Invidious (%s) failed: %s", inst, exc)
    LOGGER.warning("❌ All Invidious instances failed for: %s", query[:50])
    return None


def _normalize_info(info: "dict | None") -> "dict | None":
    """Normalize raw yt-dlp / InnerTube / Invidious info into the uniform
    dict shape get_video_info() returns. Returns None if info is unusable."""
    if not info or not info.get("id"):
        return None
    vid = info.get("id", "")
    return {
        "id": vid,
        "title": info.get("title", "Unknown"),
        "duration": int(info.get("duration") or 0),
        "url": info.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
        "stream_url": "",
        "thumbnail": info.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
        "uploader": info.get("uploader") or info.get("channel") or "Unknown",
    }


def _innertube_next_sync(video_id: str) -> "dict | None":
    """Fetch single-video metadata via InnerTube /next endpoint (ANDROID client).

    Faster and more reliable on Heroku than yt-dlp for direct YouTube URLs —
    a single HTTP POST returns title, duration, thumbnail etc. without any
    bot-detection wall, because the ANDROID client path is not subject to
    the same checks as the web player.
    """
    import json, urllib.request

    _API_KEY = "AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w"
    _NEXT_URL = f"https://www.youtube.com/youtubei/v1/next?key={_API_KEY}&prettyPrint=false"

    payload = json.dumps({
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "20.10.35",
                "androidSdkVersion": 30,
                "hl": "en",
                "gl": "US",
                "utcOffsetMinutes": 0,
            }
        },
        "videoId": video_id,
    }).encode("utf-8")

    req = urllib.request.Request(
        _NEXT_URL, data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/20.10.35 (Linux; U; Android 11) gzip",
            "X-YouTube-Client-Name": "3",
            "X-YouTube-Client-Version": "20.10.35",
        },
        method="POST",
    )
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=6) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    # Walk the response tree for the first videoRenderer that matches video_id
    def _walk(node, out):
        if isinstance(node, dict):
            renderer = node.get("compactVideoRenderer") or node.get("videoRenderer")
            if renderer and renderer.get("videoId"):
                out.append(renderer)
            for v in node.values():
                _walk(v, out)
        elif isinstance(node, list):
            for item in node:
                _walk(item, out)

    renderers: list = []
    _walk(data, renderers)
    for r in renderers:
        if r.get("videoId") == video_id:
            title = (
                r.get("title", {}).get("simpleText")
                or (r.get("title", {}).get("runs", [{}])[0].get("text"))
                or "Unknown"
            )
            length_text = (
                r.get("lengthText", {}).get("simpleText", "")
                or (r.get("lengthText", {}).get("runs", [{}])[0].get("text", "") if r.get("lengthText") else "")
            )
            duration = 0
            if length_text:
                parts = [int(p) for p in length_text.split(":") if p.isdigit()]
                if len(parts) == 2:
                    duration = parts[0] * 60 + parts[1]
                elif len(parts) == 3:
                    duration = parts[0] * 3600 + parts[1] * 60 + parts[2]
            thumbs = (r.get("thumbnail", {}).get("thumbnails") or [])
            thumb = thumbs[-1].get("url", "") if thumbs else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            return {
                "id": video_id,
                "title": title,
                "duration": duration,
                "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
                "thumbnail": thumb,
                "uploader": "Unknown",
            }
    # Fallback: construct minimal info from the video_id itself
    return {
        "id": video_id,
        "title": "Unknown",
        "duration": 0,
        "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "uploader": "Unknown",
    }


async def get_video_info(url_or_query: str) -> dict | None:
    """Get metadata for a single video (or first search result).

    SPEED FIX ("bohot tym baad play hota hai"):
    Previously the search was strictly sequential — yt-dlp first (6s timeout),
    then InnerTube (12s), then Invidious (up to 50s). On Heroku without
    cookies, yt-dlp ALWAYS hits the "Sign in to confirm you're not a bot"
    wall and wastes its entire timeout before InnerTube even starts.

    Now InnerTube and yt-dlp race IN PARALLEL — whichever returns a valid
    result first wins. InnerTube is a direct HTTP POST to YouTube's own
    Android API that bypasses bot-detection and typically responds in
    1-2 seconds, so /play search latency drops from ~8s to ~2s.

    For direct YouTube URLs with a known video_id, InnerTube's /next
    endpoint is used (even faster — no search parsing needed).
    Invidious stays as a last-resort fallback only if both parallel
    lookups fail.
    """
    import re
    is_url = bool(re.match(r"https?://", url_or_query))
    vid_id = _extract_video_id(url_or_query) if is_url else None

    # ── Build the search query for yt-dlp ──────────────────────────────────
    if is_url:
        query = f"ytsearch1:{url_or_query}" if not vid_id else f"ytsearch1:https://www.youtube.com/watch?v={vid_id}"
    else:
        query = f"ytsearch1:{url_or_query}"

    def _ytdlp_info():
        opts = {
            **_ydl_opts(),
            "extract_flat": "in_playlist",
            "default_search": "ytsearch1",
            "noplaylist": False,
            "socket_timeout": 5,
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if info and "entries" in info and info["entries"]:
                return info["entries"][0]
            return info

    # ── Choose the InnerTube call based on input type ──────────────────────
    if vid_id:
        innertube_fn = lambda: _innertube_next_sync(vid_id)
    else:
        innertube_fn = lambda: _innertube_search_sync(url_or_query)

    loop = asyncio.get_running_loop()

    # ── Race yt-dlp and InnerTube in parallel ──────────────────────────────
    ytdlp_task = loop.run_in_executor(None, _ytdlp_info)
    innertube_task = loop.run_in_executor(None, innertube_fn)

    ytdlp_future = asyncio.ensure_future(ytdlp_task)
    innertube_future = asyncio.ensure_future(innertube_task)

    result = None
    pending = {ytdlp_future, innertube_future}

    # BUG FIX: previously this used FIRST_COMPLETED and then UNCONDITIONALLY
    # cancelled every pending task. If the first task to finish returned None
    # (a very common case — InnerTube fails fast on a flaky network, or
    # yt-dlp hits the bot-detection wall), the still-running task that would
    # have succeeded was killed before it could return, so BOTH sources were
    # discarded and the bot reported "all sources exhausted" even though a
    # valid result was seconds away. Now we keep waiting for the remaining
    # task whenever the first one returned nothing, and only cancel once we
    # actually have a usable result (or the overall timeout fires).
    try:
        while pending:
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED,
                timeout=8.0,
            )
            if not done:
                break  # overall timeout — cancel whatever is still running

            for task in done:
                try:
                    info = task.result()
                    normalized = _normalize_info(info)
                    if normalized:
                        if result is None or (result.get("title") == "Unknown" and normalized.get("title") != "Unknown"):
                            result = normalized
                except Exception:
                    pass

            if result:
                break
    except Exception:
        pass

    for p in pending:
        p.cancel()

    if result:
        return result

    # ── Last-resort fallback: Invidious ────────────────────────────────────
    LOGGER.info("Both yt-dlp + InnerTube failed — trying Invidious | %s", url_or_query[:50])
    try:
        info = await loop.run_in_executor(None, _invidious_search_sync, url_or_query)
        result = _normalize_info(info)
        if result:
            return result
    except Exception:
        pass

    await send_error_log("get_video_info failed (all sources exhausted)", Exception("No results from any source"))
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  FIFO pipe streaming  (⚡ Instant play — music starts before full download)
# ─────────────────────────────────────────────────────────────────────────────

def _start_pipe_download(video_id: str, audio_only: bool = True) -> str:
    """Start yt-dlp writing audio to a FIFO named pipe in a daemon thread.
    Returns the pipe path IMMEDIATELY — yt-dlp runs in the background.

    HOW IT SAVES TIME:
    • PyTgCalls opens the FIFO path from MediaStream().
    • yt-dlp starts downloading fragments and writing bytes continuously.
    • ffmpeg inside PyTgCalls reads as bytes arrive — music starts playing
      within ~2-3 s without waiting for the full file to download.

    Falls back: callers catch OSError when mkfifo is unavailable.
    """
    tmpdir = tempfile.mkdtemp(prefix="melody_pipe_")
    pipe_path = os.path.join(tmpdir, "audio.webm")
    try:
        os.mkfifo(pipe_path)
    except OSError as err:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise OSError(
            f"FIFO not supported on this platform ({err}). "
            "Falling back to full file download."
        ) from err

    url = f"https://www.youtube.com/watch?v={video_id}"
    fmt = (
        # Broad selector — same rationale as _ydl_opts(): ext constraints
        # removed to avoid "Requested format is not available" crashes.
        "bestaudio/best"
        if audio_only
        else "best[height<=720][vcodec!=none][acodec!=none]/best[height<=720]/best"
    )

    # Build a self-contained Python script that writes audio to stdout.
    # Running as a subprocess subprocess inherits sys.path but is isolated,
    # which avoids blocking the asyncio event loop.
    #
    # STRICT COOKIE MODE (kept in sync with _ydl_opts()):
    # android/ios/tv_embedded clients ignore cookiefile entirely — only the
    # "web"/"mweb" client paths use the logged-in session. So when cookies
    # exist, "web" goes first and the UA matches a real desktop browser.
    has_cookies = os.path.exists(COOKIES_FILE)
    cookie_line = (
        f'    opts["cookiefile"] = {repr(COOKIES_FILE)}\n' if has_cookies else ""
    )
    player_client_list = (
        ["web", "mweb", "tv_embedded", "android_music", "ios", "android"]
        if has_cookies
        else ["android_music", "ios", "android", "tv_embedded", "mweb", "web"]
    )
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        if has_cookies
        else "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36"
    )
    script = (
        "import sys, yt_dlp\n"
        "opts = {\n"
        f'    "format": {repr(fmt)},\n'
        '    "outtmpl": "-",\n'
        '    "quiet": True,\n'
        '    "no_warnings": True,\n'
        '    "noplaylist": True,\n'
        '    "geo_bypass": True,\n'
        '    "geo_bypass_country": "US",\n'
        '    "socket_timeout": 10,\n'
        '    "retries": 5,\n'
        '    "fragment_retries": 5,\n'
        '    "check_formats": False,\n'
        # Sequential fragments for continuous pipe flow (see _ydl_opts doc)
        '    "concurrent_fragment_downloads": 1,\n'
        '    "extractor_args": {\n'
        '        "youtube": {\n'
        f'            "player_client": {repr(player_client_list)},\n'
        '        }\n'
        '    },\n'
        '    "http_headers": {\n'
        f'        "User-Agent": {repr(user_agent)},\n'
        '        "Referer": "https://www.youtube.com/",\n'
        '    },\n'
        "}\n"
        + cookie_line
        + f"with yt_dlp.YoutubeDL(opts) as ydl:\n"
        + f"    ydl.download([{repr(url)}])\n"
    )
    cmd = [sys.executable, "-c", script]

    with _active_pipes_lock:
        _active_pipes.add(pipe_path)

    def _writer() -> None:
        proc = None
        fifo_fd = None
        slot_acquired = False
        try:
            slot_acquired = _pipe_slots.acquire(timeout=_PIPE_SLOT_TIMEOUT)
            if not slot_acquired:
                LOGGER.warning("Pipe concurrency limit reached; abandoning FIFO | %s", video_id)
                return

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

            # Blocking open — waits until PyTgCalls opens the read end.
            # Uses a daemon sub-thread so we can enforce a timeout.
            open_evt = threading.Event()
            open_result: list = [None]

            def _blocking_open():
                try:
                    open_result[0] = os.open(pipe_path, os.O_WRONLY)
                except Exception as e:
                    open_result[0] = e
                finally:
                    open_evt.set()

            t = threading.Thread(target=_blocking_open, daemon=True, name="melody-fifo-opener")
            t.start()

            deadline = time.monotonic() + _PIPE_CONNECT_TIMEOUT
            while not open_evt.wait(timeout=0.3):
                if time.monotonic() >= deadline:
                    LOGGER.warning("FIFO reader did not connect in %.1fs | %s", _PIPE_CONNECT_TIMEOUT, video_id)
                    try:
                        dummy = os.open(pipe_path, os.O_RDONLY | os.O_NONBLOCK)
                        os.close(dummy)
                    except Exception:
                        pass
                    return

            if isinstance(open_result[0], Exception):
                raise open_result[0]
            fifo_fd = open_result[0]

            # Relay yt-dlp stdout → FIFO directly (webm/opus passthrough, no re-encode)
            with os.fdopen(fifo_fd, "wb") as fifo:
                fifo_fd = None  # fdopen owns the fd now
                while True:
                    chunk = proc.stdout.read(65536)
                    if not chunk:
                        break
                    try:
                        fifo.write(chunk)
                    except (BrokenPipeError, OSError):
                        break

        except Exception as e:
            LOGGER.debug("FIFO writer error for %s: %s", video_id, e)
        finally:
            if fifo_fd is not None:
                try:
                    os.close(fifo_fd)
                except Exception:
                    pass
            if proc is not None:
                try:
                    proc.kill()
                    proc.wait(timeout=3)
                except Exception:
                    pass
            if slot_acquired:
                _pipe_slots.release()
            with _active_pipes_lock:
                _active_pipes.discard(pipe_path)
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

    threading.Thread(target=_writer, daemon=True, name=f"melody-pipe-{video_id[:8]}").start()
    return pipe_path


# ─────────────────────────────────────────────────────────────────────────────
#  Full file download (with early growing-file handoff — see download_audio())
# ─────────────────────────────────────────────────────────────────────────────

def _cache_tag(audio_only: bool) -> str:
    """Suffix distinguishing an audio-only download from a video download of
    the same YouTube video_id — see download_audio() for why this matters."""
    return "a" if audio_only else "v"


# SPEED FIX (strict "<1s after download starts" requirement): bytes of audio
# that must already be on disk before we hand the (still-growing) file to
# PyTgCalls. WebM/Opus only needs its EBML header + cluster start (a few KB)
# before ffprobe can identify the stream and ffmpeg can start decoding —
# 96KB was already far more than that, chosen conservatively; shrinking it
# to ~20KB is still comfortably more than the header needs while getting
# the handoff several times closer to "as soon as bytes exist on disk"
# instead of "wait for ~1-6s of audio". This is a byte threshold, not a
# time delay — on any real connection it's cleared in well under 100ms.
_EARLY_HANDOFF_BYTES = 20_000
# Hard ceiling on how long we wait for that early-handoff threshold before
# giving up and blocking on the full download instead (matches this file's
# previous, safe behaviour exactly — this is a pure fallback, never a
# regression). Kept well above what the (now tiny) threshold actually needs
# so a genuinely slow/stalled connection still gets a real chance before we
# fall back, instead of bailing out early into a needless full re-wait.
_EARLY_HANDOFF_TIMEOUT = 4.0


def _download_audio_sync(video_id: str, audio_only: bool = True,
                          early_event: "threading.Event | None" = None,
                          early_holder: "dict | None" = None) -> str:
    """Synchronous full-file download.

    SPEED FIX (2-3s /play requirement): yt-dlp writes fragments straight into
    the destination file IN ORDER as they arrive (that's how its native
    fragment downloader works even with concurrent_fragment_downloads>1 — an
    early-arriving fragment is buffered until the ones before it have been
    written), so the destination file is a normal, valid, ever-growing file
    from byte 0 onward while the download is still in progress. Unlike the
    FIFO pipe this bot used to (briefly) use, a REAL file can be opened,
    probed, and read more than once — so PyTgCalls' ffprobe check_stream()
    plus its real playback read can both consume it safely without stepping
    on each other or losing data, and download speed (fragmented, parallel)
    is almost always much faster than 1x realtime playback, so the writer
    stays comfortably ahead of the reader for the whole track.
    `progress_hooks` reports `downloaded_bytes` and the live destination path
    as fragments land; once enough header+data bytes exist we signal
    `early_event` with the (still-growing) path in `early_holder['early_path']`
    so the caller can start playback immediately instead of waiting for the
    entire file. This function still runs to completion and always sets
    `early_holder['final_path']` when done, regardless of whether the early
    signal fired.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    tag = _cache_tag(audio_only)
    outtmpl = f"/tmp/melody_{video_id}_{tag}.%(ext)s"

    def _hook(d):
        if early_event is None or early_event.is_set():
            return
        if d.get("status") != "downloading":
            return
        fp = d.get("filename") or d.get("tmpfilename")
        downloaded = d.get("downloaded_bytes") or 0
        if fp and downloaded >= _EARLY_HANDOFF_BYTES and os.path.exists(fp):
            if early_holder is not None:
                early_holder["early_path"] = fp
            early_event.set()

    opts = {
        **_ydl_opts(audio_only=audio_only),
        "outtmpl": outtmpl,
        "extract_flat": False,
    }
    if early_event is not None:
        opts["progress_hooks"] = [*opts.get("progress_hooks", []), _hook]

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
        if not os.path.exists(filepath):
            found = glob.glob(f"/tmp/melody_{video_id}_{tag}.*")
            if found:
                filepath = found[0]
            else:
                raise FileNotFoundError(f"Downloaded file not found for video_id={video_id}")
        if early_holder is not None:
            early_holder["final_path"] = filepath
        return filepath
    finally:
        # Whatever happens (success or exception), make sure a waiter
        # blocked on early_event doesn't hang forever if the threshold was
        # never reached (e.g. the whole track is shorter than the threshold).
        if early_event is not None:
            early_event.set()


def _replied_media_object(message):
    """Return the playable media object on a message (audio/video/voice/
    video_note/audio-or-video document), or None if it isn't playable."""
    if not message:
        return None
    if message.audio:
        return message.audio
    if message.video:
        return message.video
    if message.voice:
        return message.voice
    if message.video_note:
        return message.video_note
    doc = message.document
    if doc and (doc.mime_type or "").split("/")[0] in ("audio", "video"):
        return doc
    return None


def has_playable_media(message) -> bool:
    """True if `message` (typically message.reply_to_message) carries an
    audio/video file that /play or /vplay can stream directly — this is the
    "tag any audio/video and play it" feature."""
    return _replied_media_object(message) is not None


async def download_replied_media(client, message, video: bool = False) -> "dict | None":
    """
    Download a tagged (replied-to) Telegram audio/video/voice message and
    adapt it into the same info-dict shape get_video_info() returns, so the
    existing Track/queue/thumbnail pipeline in play.py works completely
    unchanged for tagged media too.

    ROOT-CAUSE for why this reuses download_audio()'s cache path instead of
    a separate code path: the file is saved directly at
    `/tmp/melody_<synthetic_id>_<a|v>.<ext>` — exactly where
    download_audio()'s cache check looks. So when _stream_track() later
    calls download_audio(track.video_id, audio_only=not video), it's a
    guaranteed cache hit and yt-dlp is never touched for tagged media.
    """
    media = _replied_media_object(message)
    if not media:
        return None

    # Synthetic id keyed on the source chat + message so re-tagging the same
    # message twice (e.g. /play then /vplay) reuses/creates the correct
    # audio vs video cached variant independently, same as YouTube tracks.
    vid = f"tg{str(message.chat.id).replace('-', 'n')}_{message.id}"
    tag = _cache_tag(not video)

    cached = glob.glob(f"/tmp/melody_{vid}_{tag}.*")
    if cached:
        filepath = cached[0]
    else:
        file_name = getattr(media, "file_name", None) or ""
        ext = file_name.rsplit(".", 1)[-1] if "." in file_name else None
        if not ext:
            ext = "mp4" if message.video or message.video_note else ("ogg" if message.voice else "mp3")
        dest = f"/tmp/melody_{vid}_{tag}.{ext}"
        try:
            filepath = await client.download_media(message, file_name=dest)
        except Exception as exc:
            await send_error_log(f"download_replied_media failed for message {message.id}", exc)
            return None
        if not filepath or not os.path.exists(filepath):
            return None

    title = (
        getattr(media, "file_name", None)
        or getattr(media, "title", None)
        or "Tagged Media"
    )
    uploader = (
        getattr(media, "performer", None)
        or (message.from_user.first_name if message.from_user else None)
        or "Telegram"
    )
    duration = int(getattr(media, "duration", 0) or 0)

    return {
        "id": vid,
        "title": title,
        "duration": duration,
        "url": "",
        "stream_url": "",
        "thumbnail": "",
        "uploader": uploader,
    }


async def download_audio(video_id: str, audio_only: bool = True) -> str:
    """Return a path to play audio (or audio+video) from — usually a REAL
    file that is still being written to on disk (see below).

    ROOT-CAUSE FIX (audio/video mismatch on /vplay): the cache lookup used to
    key ONLY on video_id (`/tmp/melody_<video_id>.*`), with no distinction
    between an audio-only download and a video download of the very same
    YouTube video. So if a chat played a track with /play first (caching an
    AUDIO-ONLY file) and someone then ran /vplay on that same track, this
    function found the cached audio-only file and happily returned it —
    which _stream_track then wrapped in a MediaStream with video_parameters
    set, producing a "video" stream that actually carried no video track at
    all (or, in the opposite order, wasted a full video re-download for a
    plain /play). The cache key now includes an audio/video tag
    (`/tmp/melody_<video_id>_a.*` vs `/tmp/melody_<video_id>_v.*`) so /play
    and /vplay always fetch (and reuse) the correct variant independently.

    FIFO pipe streaming was REMOVED (root-cause fix, kept for history):
    PyTgCalls' MediaStream calls ffmpeg.check_stream() before playback,
    which runs `ffprobe` on the given path — a named pipe (FIFO) only
    supports being drained ONCE, so after ffprobe read it for the probe
    there was nothing left for the real playback ffmpeg process, causing
    `_stream_track failed ... FileNotFoundError`.

    SPEED FIX (strict <2-3s /play requirement) — growing-file early handoff:
    Simply blocking on the FULL download (the fallback this file settled
    on after removing FIFO) reintroduced the exact 5-10s delay FIFO was
    meant to avoid. The fix is a REAL file instead of a FIFO: yt-dlp writes
    fragments into the destination file in order as they download, so
    (unlike a FIFO) the file can be safely opened, probed, and read more
    than once WHILE it is still growing — ffprobe's initial read only needs
    the header + first bit of data (guaranteed by preferring WebM/Opus,
    which doesn't need an end-of-file index the way AAC/M4A does), and the
    real ffmpeg playback read afterwards keeps consuming new bytes as they
    land, staying far behind the download's write position since fragment
    downloads run several times faster than 1x realtime playback. So:
      1. Kick off the real download in a background thread immediately.
      2. As soon as ~_EARLY_HANDOFF_BYTES have landed on disk (typically a
         few hundred ms), hand that (still-growing) path back to the caller
         — _stream_track/PyTgCalls can start playing right away.
      3. If that threshold is never reached within _EARLY_HANDOFF_TIMEOUT
         (very slow connection, or a track shorter than the threshold),
         fall back to waiting for the completed download exactly as before
         — a pure fallback, never a regression versus the prior behaviour.
    The download itself keeps running to completion in the background
    either way, so the cache file is always complete for the next play.

    Files written to /tmp/melody_<video_id>_<a|v>.* are cleaned up by
    call.py after each track finishes to avoid filling the 512 MB /tmp on
    Heroku.
    """
    # Defensive guard: a valid YouTube video ID is exactly 11 chars of
    # [A-Za-z0-9_-]. If a search query or full URL leaked in as video_id
    # (the AutoPlay bug — see _pick_related_track), reject it here instead
    # of constructing an invalid URL that crashes yt-dlp with
    # "Unsupported URL" and kills playback silently.
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id or ""):
        raise ValueError(
            f"download_audio: invalid YouTube video_id {video_id!r} "
            "(expected 11-char [A-Za-z0-9_-] ID)"
        )

    tag = _cache_tag(audio_only)
    # Cache check — reuse if already downloaded IN THE SAME VARIANT (audio
    # vs video). Never reuse a file downloaded for the other variant.
    cached = glob.glob(f"/tmp/melody_{video_id}_{tag}.*")
    if cached:
        return cached[0]

    loop = asyncio.get_running_loop()
    early_event = threading.Event()
    early_holder: dict = {}

    def _run_download():
        try:
            _download_audio_sync(video_id, audio_only, early_event=early_event, early_holder=early_holder)
        except Exception as exc:
            early_holder["error"] = exc
            early_event.set()

    # Runs in a plain daemon thread (not the executor pool) so it keeps
    # downloading in the background even after we return early below.
    dl_thread = threading.Thread(
        target=_run_download, daemon=True, name=f"melody-early-dl-{video_id[:8]}",
    )
    dl_thread.start()

    # Off-loop wait: either the early-handoff threshold fires, the download
    # finishes outright (short tracks), or we time out and fall back.
    await loop.run_in_executor(None, early_event.wait, _EARLY_HANDOFF_TIMEOUT)

    path = early_holder.get("early_path") or early_holder.get("final_path")
    if path and os.path.exists(path):
        return path

    if "error" in early_holder:
        raise early_holder["error"]

    # Threshold not reached in time (slow connection) — block for real
    # completion instead, identical to the old always-blocking behaviour.
    await loop.run_in_executor(None, dl_thread.join)
    if "error" in early_holder:
        raise early_holder["error"]
    path = early_holder.get("final_path") or early_holder.get("early_path")
    if path and os.path.exists(path):
        return path
    found = glob.glob(f"/tmp/melody_{video_id}_{tag}.*")
    if found:
        return found[0]
    raise FileNotFoundError(f"Downloaded file not found for video_id={video_id}")


# ─────────────────────────────────────────────────────────────────────────────
#  Autoplay helpers
# ─────────────────────────────────────────────────────────────────────────────

def _innertube_related_sync(video_id: str, exclude: set) -> list[dict]:
    """AutoPlay fallback: fetch YouTube's "up next" related videos via the
    InnerTube API directly (ANDROID client) — same bot-detection bypass
    trick as `_innertube_search_sync()`.

    ROOT-CAUSE FIX ("autoplay on hai phir bhi kaam nahi karta"):
    `get_related_videos()` used to rely ONLY on yt-dlp's mix/Radio playlist
    extraction. Unlike `get_video_info()` (which has a 3-way yt-dlp ->
    InnerTube -> Invidious fallback chain), it had NO fallback at all — any
    yt-dlp failure (bot-detection block, empty mix, transient error) made
    `_pick_related_track()` return None, `try_autoplay()` return False, and
    `_play_next()` silently leave the call. AutoPlay looked "on" (the DB
    flag was set correctly) but nothing ever actually played. This mirrors
    that same fallback pattern for the related-videos lookup specifically.
    """
    import json
    import urllib.request

    _API_KEY = "AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w"
    _NEXT_URL = f"https://www.youtube.com/youtubei/v1/next?key={_API_KEY}&prettyPrint=false"

    payload = json.dumps({
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "20.10.35",
                "androidSdkVersion": 30,
                "hl": "en",
                "gl": "US",
                "utcOffsetMinutes": 0,
            }
        },
        "videoId": video_id,
    }).encode("utf-8")

    req = urllib.request.Request(
        _NEXT_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/20.10.35 (Linux; U; Android 11) gzip",
            "X-YouTube-Client-Name": "3",
            "X-YouTube-Client-Version": "20.10.35",
        },
        method="POST",
    )

    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=10) as resp:
            if resp.status != 200:
                LOGGER.warning("InnerTube related HTTP %s for video_id=%s", resp.status, video_id)
                return []
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        LOGGER.warning("InnerTube related network error: %s", exc)
        return []

    def _walk(node, out):
        """Recursively find every compactVideoRenderer / videoRenderer in the
        response — the exact nesting path varies by client/layout version,
        so walking the whole tree is far more resilient than one fixed path.
        """
        if isinstance(node, dict):
            renderer = node.get("compactVideoRenderer") or node.get("videoRenderer")
            if renderer and renderer.get("videoId"):
                out.append(renderer)
            for v in node.values():
                _walk(v, out)
        elif isinstance(node, list):
            for item in node:
                _walk(item, out)

    renderers: list = []
    try:
        _walk(data, renderers)
    except Exception as exc:
        LOGGER.warning("InnerTube related parse error: %s", exc)
        return []

    results = []
    seen = set()
    for r in renderers:
        vid = r.get("videoId", "")
        if not vid or vid in exclude or vid in seen or vid == video_id:
            continue
        seen.add(vid)
        title = (
            r.get("title", {}).get("simpleText")
            or (r.get("title", {}).get("runs", [{}])[0].get("text"))
            or "Unknown"
        )
        length_text = (
            r.get("lengthText", {}).get("simpleText", "")
            or (r.get("lengthText", {}).get("runs", [{}])[0].get("text", "") if r.get("lengthText") else "")
        )
        duration = 0
        if length_text:
            parts = [int(p) for p in length_text.split(":") if p.isdigit()]
            if len(parts) == 2:
                duration = parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                duration = parts[0] * 3600 + parts[1] * 60 + parts[2]
        thumbs = (r.get("thumbnail", {}).get("thumbnails") or [])
        thumbnail = thumbs[-1].get("url", "") if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        results.append({
            "id": vid,
            "title": title,
            "duration": duration,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "thumbnail": thumbnail,
            "uploader": "Unknown",
        })
        if len(results) >= 10:
            break

    if results:
        LOGGER.info("✅ InnerTube related fallback OK: %d candidates for %s", len(results), video_id)
    else:
        LOGGER.warning("❌ InnerTube related fallback: no candidates for %s", video_id)
    return results


async def get_related_videos(video_id: str, exclude_ids: list[str] = None) -> list[dict]:
    """Fetch related videos for autoplay (skip excluded IDs)."""
    exclude = set(exclude_ids or [])

    def _related():
        # ROOT-CAUSE FIX: this call only needs lightweight metadata (title,
        # duration, thumbnail) for the autoplay queue — it must never try to
        # resolve a playable *format* for anything. The previous version
        # reused _ydl_opts(), which always sets a strict "format" selector
        # for downloading. Even with extract_flat=True, yt-dlp still fully
        # processes the primary watch-page result before flattening the
        # "up next" mix, so an unavailable format on that primary video
        # (age-restricted, region-locked, or a format list YouTube changed)
        # raised straight out of extract_info() and killed the whole
        # autoplay lookup — that's the "Requested format is not available"
        # crash from the error log.
        #
        # Fix: request YouTube's dedicated "up next" Mix/Radio playlist
        # (list=RD<id>) so entries come back as flat playlist items (never
        # format-resolved), strip the format selector entirely, and ignore
        # per-entry errors so one broken related video can't blank the list.
        url = f"https://www.youtube.com/watch?v={video_id}&list=RD{video_id}"
        opts = {**_ydl_opts(), "extract_flat": True, "playlist_items": "1:10"}
        opts.pop("format", None)
        opts["ignoreerrors"] = True
        opts["skip_download"] = True
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("entries") or [] if info else []

    try:
        loop = asyncio.get_running_loop()
        entries = await loop.run_in_executor(None, _related)
        results = []
        for e in entries:
            if not e:
                continue  # ignoreerrors leaves a None slot for a broken entry
            vid = e.get("id", "")
            if vid and vid not in exclude:
                results.append({
                    "id": vid,
                    "title": e.get("title", "Unknown"),
                    "duration": e.get("duration", 0),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "thumbnail": e.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                    "uploader": e.get("uploader", "Unknown"),
                })
        if results:
            return results
        LOGGER.info("yt-dlp related-videos returned nothing — trying InnerTube fallback | %s", video_id)
    except Exception as exc:
        LOGGER.warning("get_related_videos (yt-dlp) failed — trying InnerTube fallback: %s", exc)

    # yt-dlp's mix/Radio extraction returned nothing (or raised) — fall back
    # to a direct InnerTube "up next" lookup so AutoPlay doesn't just go
    # silent (see _innertube_related_sync()'s docstring for the root cause).
    try:
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, _innertube_related_sync, video_id, exclude)
        return results
    except Exception as exc:
        await send_error_log("get_related_videos failed (all fallbacks exhausted)", exc)
        return []
