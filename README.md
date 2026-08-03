# 🎶 Melody — Telegram Music Bot

A premium Telegram music bot that streams from YouTube with beautiful play cards, colored controls via Mini App, AutoPlay, lyrics, and more.

---

## 🚀 Setup

### 1. Clone the repository
```bash
git clone https://github.com/thomas82822/Melody_music
cd Melody_music
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your values — see .env.example for all required fields
```

### 4. Run the bot
```bash
python -m melody
```

---

## ⚙️ Required Variables

| Variable | Description |
|----------|-------------|
| `API_ID` | From [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | From [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `MONGO_DB_URI` | MongoDB Atlas connection string |
| `STRING_SESSION` | Pyrogram string session of assistant account |
| `OWNER_ID` | Your Telegram numeric user ID |
| `LOG_GROUP_ID` | Private group for error logs |
| `WEBAPP_URL` | HTTPS URL for the Web App controls page |

See `.env.example` for all optional variables.

---

## 🌐 Web App (Colored Controls)

The Mini App at `web_app/index.html` provides colored music controls.

**Hosting options:**
- **GitHub Pages** (free): Enable Pages on the `/web_app` folder
- **Vercel** (free): Deploy the `web_app/` folder
- **Railway**: Serve as a static file

Set `WEBAPP_URL` to the HTTPS URL of `index.html`.

---

## 🚢 Deploy on Railway

1. Connect your GitHub repo to Railway
2. Set all env vars in the Railway dashboard (never commit `.env`)
3. Railway will use `Procfile` automatically

---

## 📋 Commands

### Music
`/play` `/vplay` `/queue` `/skip` `/pause` `/resume` `/stop` `/seek` `/rewind` `/volume` `/mute` `/unmute` `/loop` `/loopall` `/noloop` `/shuffle` `/clearqueue` `/remove` `/np` `/lyrics` `/speed` `/autoplay` `/search`

### Admin (group admins)
`/auth` `/unauth` `/authlist` `/ban` `/unban`

### General
`/start` `/help` `/ping` `/about` `/stats`

---

## 🔒 Privacy

- Owner identity is **never** exposed in any user-facing message or log
- All errors and tracebacks go to `LOG_GROUP_ID` only
- No real names, GitHub details, or server info shown to users

---

*Made with 💛 by an anonymous developer 🌑*
