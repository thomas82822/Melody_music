# 🎶 Melody — Telegram Music Bot

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/Pyrogram-2.0.106-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/PyTgCalls-0.9.32-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/MongoDB-Atlas-brightgreen?style=for-the-badge&logo=mongodb" />
</p>

<p align="center">
  <b>Premium Telegram Music Bot • YouTube Streaming • AutoPlay • Lyrics • Colored Mini-App Controls</b>
</p>

---

## 🚀 Deploy on Heroku

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/thomas82822/Melody_music)

> Click the button above → Fill in env vars → Deploy! Bot will start automatically.

---

## ⚙️ Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `API_ID` | From [my.telegram.org](https://my.telegram.org) | ✅ |
| `API_HASH` | From [my.telegram.org](https://my.telegram.org) | ✅ |
| `BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) | ✅ |
| `MONGO_DB_URI` | MongoDB Atlas connection string | ✅ |
| `STRING_SESSION` | Pyrogram string session of assistant | ✅ |
| `OWNER_ID` | Your Telegram numeric user ID | ✅ |
| `LOG_GROUP_ID` | Private group ID for error logs | ✅ |
| `OWNER_NAME` | Alias shown in play cards (default: Maestro) | ❌ |
| `WEBAPP_URL` | HTTPS URL for colored controls mini-app | ❌ |
| `BOT_USERNAME` | Your bot's @username | ❌ |
| `GENIUS_API_TOKEN` | From [genius.com/api-clients](https://genius.com/api-clients) | ❌ |
| `YT_COOKIES` | Base64-encoded cookies.txt for YouTube | ❌ |
| `MAX_DURATION` | Max song duration in seconds (default: 3600) | ❌ |
| `AUTOPLAY` | Enable autoplay by default (default: true) | ❌ |

---

## 📋 All Commands

### 🎵 Music
| Command | Description |
|---------|-------------|
| `/play [song/url]` | Play from YouTube |
| `/vplay [song/url]` | Video stream |
| `/queue` or `/q` | Show current queue |
| `/skip` or `/s` | Skip current song |
| `/pause` | Pause playback |
| `/resume` | Resume playback |
| `/stop` | Stop music + clear queue |
| `/seek [sec]` | Seek forward N seconds |
| `/rewind [sec]` | Rewind N seconds |
| `/np` | Now playing info |
| `/shuffle` | Shuffle queue |
| `/clearqueue` | Clear entire queue |
| `/remove [pos]` | Remove track at position |
| `/search [query]` | Inline YouTube search |

### ⚙️ Settings
| Command | Description |
|---------|-------------|
| `/volume [1-200]` | Set volume level |
| `/mute` | Mute audio |
| `/unmute` | Unmute (restores to 100) |
| `/loop` | Loop current song |
| `/loopall` | Loop entire queue |
| `/noloop` | Disable loop |
| `/speed [0.5-2.0]` | Playback speed |
| `/autoplay on/off` | Toggle autoplay |

### ℹ️ Info
| Command | Description |
|---------|-------------|
| `/lyrics [song]` | Fetch lyrics from Genius |
| `/ping` | Bot latency |
| `/stats` | Bot statistics (uptime, RAM, chats) |
| `/about` | About Melody (anonymous) |
| `/start` | Welcome message |
| `/help` | Inline categorized help |

### 👑 Admin (group admins only)
| Command | Description |
|---------|-------------|
| `/auth [user]` | Authorize user to use bot commands |
| `/unauth [user]` | Remove authorization |
| `/authlist` | List authorized users |
| `/ban [user]` | Ban user from using bot |
| `/unban [user]` | Unban user |

### 🔒 Owner (hidden from /help)
| Command | Description |
|---------|-------------|
| `/reboot` | Full process restart |
| `/restart` | Same as /reboot |
| `/reload` | Hot-reload all plugins (no restart) |
| `/update` | Git pull + restart |
| `/shell [cmd]` | Run shell command |
| `/eval [code]` | Evaluate Python code |
| `/logs` | Send bot log file |
| `/stats` | Full stats (owner sees more) |
| `/gban [user]` | Global ban user |
| `/ungban [user]` | Remove global ban |
| `/broadcast` | Mass message all chats |
| `/chatlist` | List all served chats |
| `/maintenance on/off` | Toggle maintenance mode |

---

## 🌐 Web App (Colored Controls)

The Mini App at `web_app/index.html` gives users colored music control buttons inside Telegram.

**Host it (HTTPS required):**

**Option A — GitHub Pages (free, easiest):**
1. Go to repo **Settings → Pages**
2. Source: `Deploy from branch` → `main` → `/web_app`
3. Your URL: `https://thomas82822.github.io/Melody_music/index.html`
4. Set `WEBAPP_URL` to that URL

**Option B — Vercel (free):**
1. Import `web_app/` folder to Vercel
2. Set `WEBAPP_URL` to the Vercel HTTPS URL

---

## 🚢 Manual Setup

```bash
git clone https://github.com/thomas82822/Melody_music
cd Melody_music
pip install -r requirements.txt
cp .env.example .env
# Fill in .env values
python -m melody
```

---

## 🔒 Privacy

- Owner identity is **never** exposed in any user-facing message
- All errors → `LOG_GROUP_ID` only (private)
- No real names, GitHub details, or server info shown to users
- `.env` is in `.gitignore` — never committed

---

*Made with 💛 by an anonymous developer 🌑*
