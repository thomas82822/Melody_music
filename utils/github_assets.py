"""
📦 GitHub-backed persistent assets (start pic, welcome-group pic, etc.)

WHY THIS EXISTS
════════════════
Heroku (and most PaaS dynos) wipe the filesystem on every restart/redeploy,
so anything saved only to the local `assets/` folder (e.g. via /setpic)
disappears the moment the dyno cycles. Pushing the file to the bot's own
GitHub repo on save is only half the fix — the bot must also PULL it back
down from GitHub on startup, before it's needed, or the "permanent" copy on
GitHub never makes it back onto the fresh dyno's disk.

Requires Config.GITHUB_TOKEN (PAT with repo write access) and
Config.GITHUB_REPO ("username/reponame"). Both push and pull are
best-effort: any failure is reported/logged but never blocks the bot.
"""
import base64
import os

from melody.config import Config
from melody.logging import LOGGER

_GH_API_BASE = "https://api.github.com"


def _headers() -> dict:
    return {
        "Authorization": f"token {Config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def push_to_github(local_path: str, gh_path: str, commit_message: str) -> tuple[bool, str]:
    """Upload local_path to Config.GITHUB_REPO at gh_path via the Contents API.

    Returns (success, message).
    """
    token = Config.GITHUB_TOKEN
    repo = Config.GITHUB_REPO
    if not token or not repo:
        return False, "GITHUB_TOKEN / GITHUB_REPO not set in .env — skipping GitHub push."

    try:
        import aiohttp
    except ImportError:
        return False, "aiohttp not installed — cannot push to GitHub."

    try:
        with open(local_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode()
    except OSError as e:
        return False, f"Could not read local file: {e}"

    url = f"{_GH_API_BASE}/repos/{repo}/contents/{gh_path}"

    async with aiohttp.ClientSession() as session:
        # 1. Check if the file already exists (need its SHA to update it)
        sha = None
        async with session.get(url, headers=_headers()) as resp:
            if resp.status == 200:
                data = await resp.json()
                sha = data.get("sha")

        # 2. Create or update the file
        payload: dict = {"message": commit_message, "content": content_b64}
        if sha:
            payload["sha"] = sha

        async with session.put(url, headers=_headers(), json=payload) as resp:
            if resp.status in (200, 201):
                return True, "Image pushed to GitHub ✅"
            body = await resp.text()
            return False, f"GitHub API error {resp.status}: {body[:200]}"


async def pull_from_github(local_path: str, gh_path: str) -> bool:
    """Download gh_path from Config.GITHUB_REPO into local_path if it exists
    on GitHub. Returns True if a file was written locally.

    Safe to call even when local_path already exists — used on startup to
    restore assets wiped by an ephemeral filesystem restart. Silent no-op
    when GITHUB_TOKEN/GITHUB_REPO aren't configured, the file doesn't exist
    on GitHub, or the download fails for any reason — never blocks startup.
    """
    token = Config.GITHUB_TOKEN
    repo = Config.GITHUB_REPO
    if not token or not repo:
        return False

    try:
        import aiohttp
    except ImportError:
        return False

    url = f"{_GH_API_BASE}/repos/{repo}/contents/{gh_path}"
    headers = {**_headers(), "Accept": "application/vnd.github.raw+json"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return False
                data = await resp.read()
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(data)
        return True
    except Exception as exc:
        LOGGER.warning("Could not pull %s from GitHub: %s", gh_path, exc)
        return False


async def restore_persistent_assets(assets: list[tuple[str, str]]) -> None:
    """Restore every (local_path, gh_path) pair that's missing locally.

    Call once on startup, before any handler needs these files, so a fresh
    ephemeral dyno gets back the images saved via /setpic and
    /setwelcomepic in previous runs.
    """
    if not Config.GITHUB_TOKEN or not Config.GITHUB_REPO:
        return
    restored = 0
    for local_path, gh_path in assets:
        if os.path.exists(local_path):
            continue
        if await pull_from_github(local_path, gh_path):
            restored += 1
            LOGGER.info("Restored %s from GitHub (%s)", local_path, gh_path)
    if restored:
        LOGGER.info("Restored %d persistent asset(s) from GitHub.", restored)
