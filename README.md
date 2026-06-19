# 📡 Telegram Inactive Channel Scanner Bot

Runs 24/7 on Railway.app — scrapes TGStat, Telemetr, TelegramChannels and more every day, finds inactive channels, sends results straight to your Telegram.

---

## What you need (all free):

1. **Telegram API** — from my.telegram.org
2. **Telegram Bot** — from @BotFather
3. **Your Chat ID** — from @userinfobot
4. **Railway.app account** — free hosting

---

## Step 1 — Create your Telegram Bot

1. Open Telegram → search **@BotFather**
2. Send `/newbot`
3. Give it a name: `My Scanner Bot`
4. Give it a username: `myscanner123bot`
5. Copy the **bot token** it gives you

---

## Step 2 — Get your Chat ID

1. Open Telegram → search **@userinfobot**
2. Send `/start`
3. Copy your **Id** number

---

## Step 3 — Edit config.py

Open `config.py` and fill in:

```python
API_ID   = 12345678          # from my.telegram.org
API_HASH = "your_api_hash"   # from my.telegram.org
BOT_TOKEN = "123:ABC..."     # from @BotFather
MY_CHAT_ID = 987654321       # from @userinfobot
INACTIVE_DAYS = 180          # your threshold
SCAN_HOUR = 9                # what time to scan daily (UTC)
```

---

## Step 4 — Deploy to Railway (free hosting)

1. Go to **railway.app** and sign up free (use GitHub login)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Upload this folder to a GitHub repo first:
   - Go to **github.com** → New repository → Upload files → drag this folder
4. Connect that repo to Railway
5. Railway auto-detects the Procfile and starts the bot!

---

## Step 5 — Add session files (one time login)

First time, Railway needs you to log in to Telegram:
1. In Railway dashboard → open **Shell**
2. Type: `python bot.py`
3. Enter your phone number with country code
4. Enter the code Telegram sends you
5. Done! The session is saved forever.

---

## Commands you can send to your bot:

| Command | What it does |
|---|---|
| `/scan` | Start a manual scan right now |
| `/status` | Check how many channels scanned |

---

## What you get in Telegram every day:

```
📡 Inactive Channels Found

🔴 1+ YEAR inactive
  👤 @oldcrypto — Old Crypto News
  👥 45,230 members | 📅 Last post: 2023-01-15 (520d ago)
  🔗 t.me/oldcrypto

🟠 6+ MONTHS inactive
  👤 @defiupdates — DeFi Updates
  👥 12,100 members | 📅 Last post: 2023-08-20 (300d ago)
  🔗 t.me/defiupdates
```
