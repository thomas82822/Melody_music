# 🎶 MELODY — TELEGRAM MUSIC BOT — COMPLETE BUILD BRIEF

> **Bot Name:** Melody  
> **Theme:** Modi × Meloni — Saffron / Gold / Green patriotic  
> **Base:** Python 3.11 (Pyrogram + PyTgCalls)  
> **Host:** Railway / VPS via GitHub  
> **Music Source:** YouTube ONLY (yt-dlp)  
> **Anonymity:** STRICT — owner identity, GitHub details, all credentials NEVER exposed anywhere in code, messages, logs, or errors shown to users  

---

## 🔒 PRIVACY / ANONYMITY RULES (MANDATORY — READ FIRST)

```
❌ NEVER print, show, or mention:
   - OWNER_ID in any user-facing message
   - Real owner name (only OWNER_NAME alias is shown)
   - GitHub repo URL / username in any user-facing message
   - Any API keys, tokens, secrets in logs visible to users
   - Bot server IP or hosting provider name
   - MongoDB URI or any DB details
   - Error tracebacks to users (only to LOG_GROUP_ID)

✅ ALWAYS:
   - Send all errors/tracebacks → LOG_GROUP_ID only (private)
   - Show users only friendly error messages ("Something went wrong 🌸")
   - Use OWNER_NAME (alias like "Maestro") everywhere, not real name
   - /about shows: "Made with 💛 by an anonymous developer 🌑"
   - Owner commands are completely hidden from /help for non-owners
```

---

## 🔑 ENV VARIABLES — AGENT MUST READ FROM .env ONLY, NEVER HARDCODE

```
API_ID          = integer from my.telegram.org
API_HASH        = string from my.telegram.org
BOT_TOKEN       = string from @BotFather
MONGO_DB_URI    = mongodb+srv://... (Atlas free tier)
STRING_SESSION  = pyrogram string session of assistant account
OWNER_ID        = your Telegram numeric user ID
OWNER_NAME      = cute alias e.g. "Maestro" or "Shadow" (shown on play card)
LOG_GROUP_ID    = private group ID for error logs (e.g. -1001234567890)
YT_COOKIES      = base64 encoded YouTube cookies.txt
GENIUS_API_TOKEN= from genius.com/api-clients
MAX_DURATION    = 3600
AUTOPLAY        = true
BOT_USERNAME    = @YourMelodyBot
WEBAPP_URL      = HTTPS URL where web_app/index.html is served
```

---

## 🎨 COLOR THEME — MODI-MELONI

```python
COLORS = {
    "saffron":  "#FF6600",   # Primary — play, main actions
    "gold":     "#FFD700",   # Accent — highlights, owner name
    "green":    "#009246",   # Secondary — positive actions
    "red":      "#CE2B37",   # Danger — stop, ban
    "white":    "#FFFFFF",
    "dark":     "#1A0500",
    "overlay":  "rgba(0,0,0,0.55)",
}
```

---

## 🌐 COLORED BUTTONS — TELEGRAM WEB APP (MINI APP)

Telegram Bot API ke standard inline buttons mein color support nahi hai.  
**Solution:** Telegram Web App (Mini App) — ek HTTPS HTML page jo bot ke andar khulti hai,  
jisme full colored buttons hain CSS se.

### How it works:
1. Bot play card ke saath ek **"🎛 Controls"** button bhejta hai
2. Yeh button `web_app=WebAppInfo(url=WEBAPP_URL)` type ka hai
3. User tap kare toh Telegram ke andar ek mini popup khulta hai
4. Usme saffron/gold/green colored buttons hain music controls ke liye
5. Buttons press hone par `Telegram.WebApp.sendData(action)` se bot ko data milta hai
6. Bot `web_app_data` filter se data receive karta hai aur action leta hai

### web_app/index.html — Full Code:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Melody Controls</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      background: linear-gradient(160deg, #1A0500 0%, #3D0F00 50%, #1A0500 100%);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 20px;
      font-family: 'Segoe UI', sans-serif;
    }

    .title {
      color: #FFD700;
      font-size: 22px;
      font-weight: bold;
      margin-bottom: 6px;
      letter-spacing: 2px;
    }

    .subtitle {
      color: #FF6600;
      font-size: 13px;
      margin-bottom: 28px;
      opacity: 0.85;
    }

    .divider {
      width: 100%;
      height: 1px;
      background: linear-gradient(90deg, transparent, #FF6600, transparent);
      margin: 16px 0;
    }

    .btn-grid {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 12px;
      width: 100%;
      max-width: 360px;
    }

    .btn-grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      width: 100%;
      max-width: 360px;
      margin-top: 12px;
    }

    .btn {
      border: none;
      border-radius: 14px;
      padding: 16px 8px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      color: #fff;
      letter-spacing: 0.5px;
      transition: transform 0.12s, opacity 0.12s;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    }

    .btn:active { transform: scale(0.93); opacity: 0.85; }

    .btn .icon { font-size: 22px; }

    /* SAFFRON — play / resume / main actions */
    .btn-saffron {
      background: linear-gradient(135deg, #FF6600, #FF8C00);
      box-shadow: 0 4px 18px rgba(255,102,0,0.45);
    }

    /* GOLD — skip / queue / info */
    .btn-gold {
      background: linear-gradient(135deg, #B8860B, #FFD700);
      color: #1A0500;
      box-shadow: 0 4px 18px rgba(255,215,0,0.4);
    }

    /* GREEN — loop / autoplay / positive */
    .btn-green {
      background: linear-gradient(135deg, #005f2e, #009246);
      box-shadow: 0 4px 18px rgba(0,146,70,0.45);
    }

    /* RED — stop / danger */
    .btn-red {
      background: linear-gradient(135deg, #8b0000, #CE2B37);
      box-shadow: 0 4px 18px rgba(206,43,55,0.45);
    }

    /* PURPLE — lyrics / extras */
    .btn-purple {
      background: linear-gradient(135deg, #4a0080, #7b2ff7);
      box-shadow: 0 4px 18px rgba(123,47,247,0.4);
    }

    /* DARK-GOLD — volume */
    .btn-dark {
      background: linear-gradient(135deg, #2a1500, #5c3000);
      border: 1px solid #FF6600;
      box-shadow: 0 4px 18px rgba(255,102,0,0.2);
    }

    .section-label {
      color: #FF6600;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 2px;
      margin: 18px 0 8px;
      text-transform: uppercase;
      align-self: flex-start;
      max-width: 360px;
      width: 100%;
    }

    .now-playing {
      background: rgba(255,102,0,0.1);
      border: 1px solid rgba(255,102,0,0.3);
      border-radius: 12px;
      padding: 14px 18px;
      width: 100%;
      max-width: 360px;
      margin-bottom: 10px;
      color: #FFD700;
      font-size: 13px;
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="title">🎶 MELODY</div>
  <div class="subtitle">Music Controls</div>

  <div class="now-playing" id="nowPlaying">♛ Your music, your vibe</div>

  <div class="divider"></div>

  <div class="section-label">▶ Playback</div>
  <div class="btn-grid">
    <button class="btn btn-saffron" onclick="send('pause')">
      <span class="icon">⏸</span>Pause
    </button>
    <button class="btn btn-saffron" onclick="send('resume')">
      <span class="icon">▶️</span>Resume
    </button>
    <button class="btn btn-gold" onclick="send('skip')">
      <span class="icon">⏭</span>Skip
    </button>
  </div>

  <div class="section-label">🔁 Loop & Queue</div>
  <div class="btn-grid">
    <button class="btn btn-green" onclick="send('loop_single')">
      <span class="icon">🔂</span>Loop 1
    </button>
    <button class="btn btn-green" onclick="send('loop_all')">
      <span class="icon">🔁</span>Loop All
    </button>
    <button class="btn btn-gold" onclick="send('shuffle')">
      <span class="icon">🔀</span>Shuffle
    </button>
  </div>

  <div class="section-label">🔊 Volume</div>
  <div class="btn-grid">
    <button class="btn btn-dark" onclick="send('vol_down')">
      <span class="icon">🔉</span>Vol -
    </button>
    <button class="btn btn-dark" onclick="send('mute')">
      <span class="icon">🔇</span>Mute
    </button>
    <button class="btn btn-dark" onclick="send('vol_up')">
      <span class="icon">🔊</span>Vol +
    </button>
  </div>

  <div class="section-label">⚡ More</div>
  <div class="btn-grid-2">
    <button class="btn btn-purple" onclick="send('lyrics')">
      <span class="icon">🎵</span>Lyrics
    </button>
    <button class="btn btn-gold" onclick="send('queue')">
      <span class="icon">📋</span>Queue
    </button>
  </div>

  <div class="divider"></div>

  <div class="btn-grid-2" style="margin-top:4px;">
    <button class="btn btn-green" onclick="send('autoplay_on')">
      <span class="icon">🤖</span>AutoPlay On
    </button>
    <button class="btn btn-red" onclick="send('stop')">
      <span class="icon">⏹</span>Stop
    </button>
  </div>

  <script>
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();

    // Set theme colors to match Modi-Meloni
    tg.setHeaderColor('#1A0500');
    tg.setBackgroundColor('#1A0500');

    function send(action) {
      tg.sendData(action);
      // Visual feedback
      setTimeout(() => tg.close(), 300);
    }

    // Show chat title if passed via start_param
    const params = new URLSearchParams(window.location.search);
    const chatTitle = params.get('chat') || '';
    if (chatTitle) {
      document.getElementById('nowPlaying').textContent = '🏛 ' + decodeURIComponent(chatTitle);
    }
  </script>
</body>
</html>
```

### Python handler for Web App data:
```python
# melody/plugins/music/webapp_handler.py
from pyrogram import Client, filters
from pyrogram.types import Message
from melody import bot
from melody.core.call import (
    pause_stream, resume_stream, skip_stream, stop_stream,
    change_volume
)
from melody.core.queue import (
    set_loop, shuffle_queue, get_volume, set_volume, set_autoplay
)

@bot.on_message(filters.web_app_data)
async def handle_webapp(client: Client, message: Message):
    chat_id = message.chat.id
    action = message.web_app_data.data

    actions = {
        "pause":        lambda: pause_stream(chat_id),
        "resume":       lambda: resume_stream(chat_id),
        "skip":         lambda: skip_stream(chat_id),
        "stop":         lambda: stop_stream(chat_id),
        "loop_single":  lambda: set_loop(chat_id, "single"),
        "loop_all":     lambda: set_loop(chat_id, "all"),
        "shuffle":      lambda: shuffle_queue(chat_id),
        "mute":         lambda: change_volume(chat_id, 0),
        "vol_up":       lambda: change_volume(chat_id, min(200, get_volume(chat_id) + 20)),
        "vol_down":     lambda: change_volume(chat_id, max(1,  get_volume(chat_id) - 20)),
        "autoplay_on":  lambda: set_autoplay(chat_id, True),
    }

    if action in actions:
        try:
            await actions[action]()
        except Exception:
            pass  # silent fail, errors go to LOG_GROUP only
```

### How to host WEBAPP_URL (HTTPS required):
```
Option A — GitHub Pages (free, easiest):
  1. Put web_app/index.html in repo
  2. Enable GitHub Pages on /web_app folder
  3. URL: https://yourusername.github.io/melody-bot/web_app/index.html
  4. Set WEBAPP_URL=https://yourusername.github.io/melody-bot/web_app/index.html

Option B — Vercel (free):
  1. Deploy web_app/ folder to Vercel
  2. Get HTTPS URL from Vercel dashboard

Option C — Railway (same app, static folder):
  Add static file serving for /webapp route in the bot's HTTP server
```

### Play card send with Web App button:
```python
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from melody.config import Config
import urllib.parse

def get_play_buttons(chat_title: str) -> InlineKeyboardMarkup:
    encoded_title = urllib.parse.quote(chat_title[:30])
    webapp_url = f"{Config.WEBAPP_URL}?chat={encoded_title}"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Pause",  callback_data="pause"),
            InlineKeyboardButton("⏭ Skip",   callback_data="skip"),
            InlineKeyboardButton("⏹ Stop",   callback_data="stop"),
        ],
        [
            InlineKeyboardButton("🎛 Colored Controls", web_app=WebAppInfo(url=webapp_url)),
        ],
        [
            InlineKeyboardButton("📋 Queue",  callback_data="queue"),
            InlineKeyboardButton("🎵 Lyrics", callback_data="lyrics"),
        ],
    ])
```

---

## 📦 FOLDER STRUCTURE

```
Melody/
├── melody/
│   ├── __init__.py
│   ├── config.py
│   ├── logging.py
│   ├── core/
│   │   ├── ytdl.py
│   │   ├── queue.py
│   │   ├── call.py
│   │   └── autoplay.py
│   └── plugins/
│       ├── music/
│       │   ├── play.py
│       │   ├── queue_cmd.py
│       │   ├── controls.py
│       │   ├── seek.py
│       │   ├── loop.py
│       │   ├── volume.py
│       │   ├── search.py
│       │   ├── lyrics.py
│       │   ├── speed.py
│       │   ├── nowplaying.py
│       │   └── webapp_handler.py
│       ├── admin/
│       │   ├── auth.py
│       │   ├── ban.py
│       │   ├── gban.py
│       │   └── broadcast.py
│       ├── misc/
│       │   ├── start.py
│       │   ├── help.py
│       │   ├── ping.py
│       │   ├── stats.py
│       │   ├── about.py
│       │   └── new_group.py
│       └── owner/
│           ├── update.py
│           ├── restart.py
│           └── logs.py
├── utils/
│   ├── database.py
│   ├── decorators.py
│   ├── formatters.py
│   └── thumbnails.py
├── web_app/
│   └── index.html          ← Colored buttons HTML
├── assets/
│   ├── bg_main.png
│   ├── bg_start.png
│   └── fonts/
│       ├── Poppins-Bold.ttf
│       ├── Poppins-Regular.ttf
│       └── NotoSans-Bold.ttf
├── strings/
│   └── themes.py
├── __main__.py
├── requirements.txt
├── Procfile
├── runtime.txt
└── .env.example
```

---

## ⚙️ AGENT BUILD PARTS (7 Parts — Each Agent-Sized)

```
PART 1 → config.py + logging.py + database.py        (~150 lines)
PART 2 → ytdl.py + queue.py                          (~200 lines)
PART 3 → call.py + autoplay.py                       (~150 lines)
PART 4 → thumbnails.py + asset generation             (~250 lines)
PART 5 → web_app/index.html (colored buttons)        (~200 lines HTML)
PART 6 → All plugins (music + admin + misc + owner)  (~500 lines)
PART 7 → __main__.py + deployment files + test       (~100 lines)
```

**Rules for each agent:**
- Do NOT exceed the assigned part scope
- After finishing, run syntax check: `find . -name "*.py" -exec python -m py_compile {} \;`
- Commit to GitHub after each part
- Never expose any env var values in code or comments
- All error logging → `LOG_GROUP_ID` only

---

## 📋 ALL COMMANDS

### 🎵 Music
```
/play [song/url]    — Play from YouTube
/vplay [song/url]   — Video stream
/queue or /q        — Show queue
/skip or /s         — Skip song
/pause              — Pause
/resume             — Resume
/stop               — Stop + clear queue
/seek [sec]         — Seek forward
/rewind [sec]       — Seek backward
/volume [1-200]     — Set volume
/mute               — Mute
/unmute             — Unmute
/loop               — Loop current song
/loopall            — Loop queue
/noloop             — Disable loop
/shuffle            — Shuffle queue
/clearqueue         — Clear queue
/remove [pos]       — Remove from queue
/np                 — Now playing
/lyrics [song]      — Genius lyrics
/speed [0.5-2.0]    — Playback speed
/autoplay on/off    — Toggle autoplay
/search [query]     — Inline YT search
```

### 👑 Admin (group admins only)
```
/auth [user]        — Authorize user
/unauth [user]      — Remove auth
/authlist           — Authorized users list
/ban [user]         — Ban from bot
/unban [user]       — Unban
```

### 🔒 Owner (hidden from /help)
```
/update             — Pull + restart
/restart            — Restart bot
/stats              — Full stats
/logs               — Send logs
/gban [user]        — Global ban
/ungban [user]      — Global unban
/maintenance on/off — Toggle maintenance
/broadcast          — Mass message
/chatlist           — All served chats
```

### 📊 General
```
/start   — Ultra-attractive Modi-Meloni welcome
/help    — Inline categorized help
/ping    — Latency
/about   — Anonymized about
/stats   — Public stats
```

---

## 🖼️ PLAY CARD LAYERS (Thumbnail 1280×720)

```
1. Background      — assets/bg_main.png (saffron gradient)
2. Dark overlay    — rgba(0,0,0,0.55) for text readability
3. Song cover      — YouTube thumbnail, circle-cropped 380×380, left side
4. Vertical divider— saffron line
5. Song title      — Poppins Bold, white, right panel
6. Artist name     — Poppins Regular, gold
7. Duration        — small, gray-white
8. Requester name  — "🙋 {user.first_name}"
9. Group name      — "🏛 {chat.title}"
10. Owner alias    — "♛ {OWNER_NAME}" (from env, never real name)
11. Progress bar   — saffron→gold gradient
12. User DP        — requester's Telegram DP, circle 70×70, bottom-left
13. Bot DP         — Melody's DP, circle 70×70, bottom-right
14. Watermark      — "🎶 Melody" semi-transparent
```

**Message buttons under play card:**
```
[⏸ Pause]  [⏭ Skip]   [⏹ Stop]
[🎛 Colored Controls]          ← Web App button (opens colored panel)
[📋 Queue]  [🎵 Lyrics]
```

---

## 🤖 AUTO-PLAY LOGIC

```
Queue empty?
  → get last played video_id from DB history
  → yt-dlp fetch related videos for that video_id
  → skip video_ids in last 15 history
  → add top result to queue
  → stream it
  → send message: "🎵 AutoPlay ▶️ {title}\n_Melody ne sunwaya!_"
Toggle: /autoplay on|off — stored per chat in MongoDB
```

---

## 🆕 NEW GROUP TRIGGER

```python
# On bot added to group:
# 1. Save chat to DB
# 2. Send bg_start.png with welcome caption
# 3. Caption includes: group name, adder's first name
# 4. Buttons: Play Now + Help
# 5. Log to LOG_GROUP_ID: chat title, chat_id, adder user_id
# ❌ NEVER log adder's username or real name to any public place
```

---

## 🚀 DEPLOYMENT

```
Platform: Railway (recommended) or any VPS
Runtime: Python 3.11

Procfile:
  worker: python -m melody

runtime.txt:
  python-3.11.9

Environment: Set all .env vars in Railway dashboard
             NEVER commit .env file to GitHub

GitHub repo:
  - .env in .gitignore
  - No hardcoded tokens/IDs anywhere in code
  - README has no owner info, just setup steps
```

---

## 📦 requirements.txt

```
pyrogram==2.0.106
tgcrypto
pytgcalls==0.9.32
yt-dlp>=2024.1.1
Pillow>=10.0.0
aiohttp
aiofiles
motor
pymongo
python-dotenv
httpx
lyricsgenius
mutagen
psutil
colorlog
uvloop
```

---

## 🐞 COMMON ERRORS + FIXES

| Error | Fix |
|-------|-----|
| `FloodWait` | `try/except FloodWait as e: await asyncio.sleep(e.value)` |
| `NoActiveGroupCall` | Handle gracefully: "Voice chat band hai, pehle VC kholo" |
| `yt_dlp DownloadError` | Try/except, tell user "Song nahi mili 🌸" |
| `Motor connection error` | Verify MONGO_DB_URI, Atlas IP whitelist |
| `PIL font not found` | Download fonts to assets/fonts/ before import |
| `STRING_SESSION invalid` | Re-run generate_session.py |
| `pytgcalls version error` | Pin: pytgcalls==0.9.32 exactly |
| WebApp not opening | WEBAPP_URL must be HTTPS, no localhost |

---

## ✅ FINAL SYNTAX CHECK (run after each part)

```bash
find . -name "*.py" -exec python -m py_compile {} \;
echo "All Python files syntax OK"
```

---

*🎶 Melody — Har dil ki awaaz. 100% original. Owner identity: NEVER revealed.*
*Build part by part. Commit after each. Test syntax, not runtime.*
