<div align="center">

<img src="https://telegra.ph/file/c0e014ff34f34d1056627.png" width="200" alt="MelodiX Logo">

# 𝙈𝙚𝙡𝙤𝙙𝙞𝙓 🎧
### High Quality Telegram Music Bot — YouTube + Cookies

<p>
  <a href="https://github.com/thomas82822/Melody_music/stargazers"><img src="https://img.shields.io/github/stars/thomas82822/Melody_music?style=for-the-badge&color=yellow"></a>
  <a href="https://github.com/thomas82822/Melody_music/fork"><img src="https://img.shields.io/github/forks/thomas82822/Melody_music?style=for-the-badge&color=orange"></a>
  <a href="https://github.com/thomas82822/Melody_music/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-GPL%20v3-blue?style=for-the-badge"></a>
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python">
</p>

> **Smooth • Lagless • High Quality** — Stream YouTube music directly in Telegram group voice chats with cookies support for zero restrictions.

---

## 🚀 Deploy to Heroku

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/thomas82822/Melody_music)

> **One-click deploy!** Click the button above. Fill in your vars and hit Deploy.

---

## 🎵 Features

| Feature | Details |
|---|---|
| 🎧 Platform | YouTube only (stable, fast, no rate limits) |
| 🍪 Cookies | YT cookies support — bypasses age-gates & bot-detection |
| 📋 Queue | Multi-track queue with skip, shuffle, loop |
| 🎛️ Controls | Play, Pause, Resume, Stop, Seek, Volume |
| 🌍 Language | Multi-language (EN, HI, AR, TR, ID, and more) |
| 📊 Stats | Detailed bot & streaming stats |
| 🔒 Admin | Full admin controls, auth system, blacklist |
| 🎤 Assistants | Up to 5 simultaneous assistant accounts |
| 🎬 Video | Video stream support in voice chats |
| 🎼 Lyrics | Song lyrics fetcher |

---

## 📋 Required Variables

| Variable | Description | Required |
|---|---|---|
| `API_ID` | Get from [my.telegram.org](https://my.telegram.org) | ✅ |
| `API_HASH` | Get from [my.telegram.org](https://my.telegram.org) | ✅ |
| `BOT_TOKEN` | Get from [@BotFather](https://t.me/BotFather) | ✅ |
| `MONGO_DB_URI` | MongoDB URI from [cloud.mongodb.com](https://cloud.mongodb.com) | ✅ |
| `LOG_GROUP_ID` | Your private log group chat ID | ✅ |
| `OWNER_ID` | Your Telegram User ID | ✅ |
| `MUSIC_BOT_NAME` | Bot name (ASCII only, e.g. `MelodiX`) | ✅ |
| `STRING1` | Pyrogram string session ([@StringFatherBot](https://t.me/StringFatherBot)) | ✅ |
| `COOKIES` | YouTube cookies.txt content (Netscape format) — fixes age-restriction errors | ❌ Recommended |
| `HEROKU_API_KEY` | Your Heroku API key | ❌ |
| `HEROKU_APP_NAME` | Your Heroku app name | ❌ |

---

## 🍪 How to get YouTube Cookies

1. Install **"Get cookies.txt LOCALLY"** extension in Chrome/Firefox
2. Open [youtube.com](https://youtube.com) and **log in**
3. Click the extension icon → Export cookies → Save as `cookies.txt`
4. Open `cookies.txt`, copy the **entire content**
5. Paste it as the value of `COOKIES` var in Heroku

> This lets yt-dlp bypass YouTube's bot-detection and age restrictions for smooth playback.

---

## 🛠️ Self-Host Setup

```bash
# 1. Clone
git clone https://github.com/thomas82822/Melody_music
cd Melody_music

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Configure
cp sample.env .env
nano .env   # fill in your values

# 4. Run
python3 -m MelodiX
```

---

## 🤖 Commands

| Command | Description |
|---|---|
| `/play [song/URL]` | Play a YouTube song |
| `/vplay [song/URL]` | Play a YouTube video |
| `/pause` | Pause current song |
| `/resume` | Resume paused song |
| `/skip` | Skip to next in queue |
| `/stop` | Stop and clear queue |
| `/queue` | Show current queue |
| `/seek [seconds]` | Seek to position |
| `/loop` | Toggle loop |
| `/shuffle` | Shuffle queue |
| `/volume [1-200]` | Set volume |
| `/lyrics [song]` | Get lyrics |
| `/ping` | Bot latency |
| `/stats` | Bot statistics |
| `/song [name]` | Download MP3/MP4 |

---

## 📞 Support

- **Bot:** [@MelodiXMusic_Bot](https://t.me/MelodiXMusic_Bot)
- **Owner:** [@TheY_CaIl_mE_OG](https://t.me/TheY_CaIl_mE_OG)

---

<p align="center">Made with ❤️ by <a href="https://t.me/TheY_CaIl_mE_OG">@TheY_CaIl_mE_OG</a></p>

</div>
