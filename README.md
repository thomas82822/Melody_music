<div align="center">

<img src="https://telegra.ph/file/c0e014ff34f34d1056627.png" width="200" alt="MelodiX Logo">

# 𝙈𝙚𝙡𝙤𝙙𝙞𝙓 🎧
### High Quality Telegram Music Bot

<p>
  <a href="https://github.com/thomas82822/Melody_music/stargazers"><img src="https://img.shields.io/github/stars/thomas82822/Melody_music?style=for-the-badge&color=yellow" alt="Stars"></a>
  <a href="https://github.com/thomas82822/Melody_music/fork"><img src="https://img.shields.io/github/forks/thomas82822/Melody_music?style=for-the-badge&color=orange" alt="Forks"></a>
  <a href="https://github.com/thomas82822/Melody_music/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-GPL%20v3-blue?style=for-the-badge" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Pyrogram-2.0+-green?style=for-the-badge" alt="Pyrogram">
</p>

> **Smooth • Lagless • High Quality** — Stream music directly in your Telegram group voice chats.

---

### 🎵 Features

| Feature | Details |
|---|---|
| 🎧 Platforms | YouTube, Spotify, Apple Music, SoundCloud, Resso, Telegram Audio |
| 📋 Queue | Multi-track queuing with skip, shuffle, loop |
| 🎛️ Controls | Play, Pause, Resume, Stop, Seek, Volume |
| 🌍 Language | Multi-language support (EN, HI, AR, TR, ID, and more) |
| 📊 Stats | Detailed bot & streaming statistics |
| 🔒 Admin | Full admin controls, auth system, blacklist |
| 🚀 Heroku | One-click Heroku deploy |
| 🎤 Assistants | Up to 5 simultaneous assistant accounts |
| 🎬 Video | Video stream support in voice chats |
| 🎼 Lyrics | Song lyrics fetcher |

---

### 🚀 Deploy to Heroku

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/thomas82822/Melody_music)

> Click the button above to deploy **𝙈𝙚𝙡𝙤𝙙𝙞𝙓 🎧** to Heroku in one click!

---

### 📋 Required Variables

| Variable | Description | Required |
|---|---|---|
| `API_ID` | Get from [my.telegram.org](https://my.telegram.org) | ✅ |
| `API_HASH` | Get from [my.telegram.org](https://my.telegram.org) | ✅ |
| `BOT_TOKEN` | Get from [@BotFather](https://t.me/BotFather) | ✅ |
| `MONGO_DB_URI` | MongoDB URI from [cloud.mongodb.com](https://cloud.mongodb.com) | ✅ |
| `LOG_GROUP_ID` | Your private log group's chat ID | ✅ |
| `OWNER_ID` | Your Telegram User ID | ✅ |
| `MUSIC_BOT_NAME` | Name for your bot (ASCII only) | ✅ |
| `STRING1` | Pyrogram string session (get from [@StringFatherBot](https://t.me/StringFatherBot)) | ✅ |
| `SPOTIFY_CLIENT_ID` | Spotify Client ID (for Spotify support) | ❌ |
| `SPOTIFY_CLIENT_SECRET` | Spotify Client Secret | ❌ |
| `HEROKU_API_KEY` | Your Heroku API key | ❌ |
| `HEROKU_APP_NAME` | Your Heroku app name | ❌ |

---

### 🛠️ Self-Host Setup

**Prerequisites:** Python 3.10+, FFmpeg

```bash
# 1. Clone the repo
git clone https://github.com/thomas82822/Melody_music
cd Melody_music

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Set environment variables
cp sample.env .env
nano .env   # Fill in your values

# 4. Run the bot
python3 -m MelodiX
```

---

### 🤖 Commands

<details>
<summary><b>▶ Player Commands</b></summary>

| Command | Description |
|---|---|
| `/play [song name or URL]` | Play a song in voice chat |
| `/vplay [song name or URL]` | Play a video in voice chat |
| `/pause` | Pause the current song |
| `/resume` | Resume paused song |
| `/skip` | Skip to next song in queue |
| `/stop` | Stop and clear queue |
| `/queue` | Show current queue |
| `/seek [seconds]` | Seek to position |
| `/loop` | Toggle loop mode |
| `/shuffle` | Shuffle the queue |
| `/volume [1-200]` | Adjust volume |

</details>

<details>
<summary><b>⚙️ Admin Commands</b></summary>

| Command | Description |
|---|---|
| `/auth` | Authorize a user to use bot |
| `/unauth` | Remove authorization |
| `/mute` | Mute assistant in voice chat |
| `/unmute` | Unmute assistant |
| `/playmode` | Change playmode (group/personal) |
| `/settings` | Open bot settings |
| `/autoend` | Toggle auto-end stream |

</details>

<details>
<summary><b>🔧 Tools</b></summary>

| Command | Description |
|---|---|
| `/lyrics [song]` | Get song lyrics |
| `/ping` | Check bot latency |
| `/stats` | Bot statistics |
| `/song [name]` | Download song as MP3/MP4 |
| `/playlist` | Play a full playlist |
| `/reload` | Reload bot plugins |

</details>

---

### 📞 Support

- **Bot:** [@MelodiXMusic_Bot](https://t.me/MelodiXMusic_Bot)
- **Owner:** [@TheY_CaIl_mE_OG](https://t.me/TheY_CaIl_mE_OG)

---

### ⭐ Credits

Built on top of [YukkiMusicBot](https://github.com/TeamYukki/YukkiMusicBot) by TeamYukki.  
Customized & maintained by [@TheY_CaIl_mE_OG](https://t.me/TheY_CaIl_mE_OG)

---

<p align="center">
  Made with ❤️ by <a href="https://t.me/TheY_CaIl_mE_OG">@TheY_CaIl_mE_OG</a>
</p>

</div>
