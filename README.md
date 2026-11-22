# Telegram Group Voice‑Chat Music Bot (py‑tgcalls v2)

A lightweight Telegram bot that streams audio from YouTube (or any yt‑dlp supported URL) directly into a group voice chat. It uses **Pyrogram**, **Py‑TgCalls v2**, **yt‑dlp**, and **FFmpeg**.

## Features
- `/play <url>` – download, convert and start streaming.
- Inline control buttons: Pause, Resume, Skip, Stop.
- `/queue` – view pending tracks.
- Auto‑queues tracks; the bot plays the next song when the current one ends.
- Works in Docker (Railway ready).

## Environment variables
| Variable | Description |
|----------|-------------|
| `API_ID` | Telegram API ID |
| `API_HASH` | Telegram API hash |
| `BOT_TOKEN` | Bot token from BotFather |
| `STRING_SESSION` | (optional) user session string for voice‑chat control |

## Deploy on Railway (quick)
1. Sign in to https://railway.app and click **New Project → Deploy from Repo**.
2. Paste the repo URL: `https://github.com/aaaditya2407-web/tg-music-bot`.
3. Railway reads `railway.toml` and builds the Docker image.
4. Add the four environment variables under **Settings → Variables**.
5. Click **Deploy** – when logs show `Bot is ready` the bot is live.

## Local run (Docker)
```bash
# Clone the repo
git clone https://github.com/aaaditya2407-web/tg-music-bot && cd tg-music-bot

# Build the image
docker build -t tg-music-bot .

# Run (replace env values)
docker run -e API_ID=1234567 -e API_HASH=yourhash -e BOT_TOKEN=123:ABC -e STRING_SESSION=yourstring tg-music-bot
```

## Credits
- Inspired by YukkiMusic / AnonXMusic projects.
- Uses open‑source libraries: **Pyrogram**, **Py‑TgCalls**, **yt‑dlp**, **ffmpeg‑python**.
