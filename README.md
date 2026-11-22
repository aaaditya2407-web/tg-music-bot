# Telegram Music Bot

A lightweight Telegram music streaming bot that plays audio from YouTube in group voice chats.

## Features
- `/play <query|url>` – search YouTube or play a direct link
- Queue management (`/queue`, `/skip`, `/clear`)
- Pause / resume (`/pause`, `/resume`)
- `/stop` – leaves voice chat and clears queue
- Admin‑only controls (toggle in `bot.py`)
- Dockerized, ready for Railway / Render / any VPS

## Prerequisites
- Telegram Bot token from **@BotFather**
- A group where the bot is added as an admin with *Can manage voice chats*
- Docker (if you run locally)

## Deployment on Railway (one‑click)
1. Create a new project → **Deploy from GitHub** → paste the repo URL.
2. Add an environment variable `BOT_TOKEN` with your Bot token.
3. Click **Deploy** – Railway reads `railway.toml`, builds the Docker image and starts the bot.
4. Open the **Logs** tab to confirm the bot started.

## Local Docker Run
```bash
# clone repo
git clone https://github.com/yourusername/tg-music-bot.git
cd tg-music-bot
# build image
docker build -t tg-music-bot .
# run container (replace TOKEN with your bot token)
docker run -e BOT_TOKEN=YOUR_BOT_TOKEN tg-music-bot
```

## Usage (in a group voice chat)
1. Start a voice chat in the group.
2. Send `/play never gonna give you up` (or any YouTube URL).
3. Use `/skip`, `/pause`, `/resume`, `/queue`, `/stop` as needed.

## Credits
- `python-telegram-bot` – Telegram Bot API wrapper
- `yt-dlp` – YouTube audio extraction
- `pytgcalls` – Telegram voice chat client

---
*This bot is MIT licensed. Feel free to fork and improve!*