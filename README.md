# Telegram Music Bot

A minimal music bot for Telegram groups using **python-telegram-bot**, **PyTgCalls**, and **yt-dlp**.

## Features
- Join voice chat (`/join`)
- Play YouTube audio (`/play <YouTube URL>`)
- Skip current track (`/skip`)
- Stop and leave voice chat (`/stop`)
- Dockerfile for containerised deployment
- Railway.toml for one‑click Railway deployment

## Environment Variables
| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram Bot API token from @BotFather |
| `API_ID` | Telegram API ID (obtain from my.telegram.org) |
| `API_HASH` | Telegram API Hash |
| `SESSION_STRING` | String session of a **user account** (required for voice chat). Generate with `telethon` or `pyrogram` utilities |

## Deployment (Railway)
1. Fork or clone the repo.
2. Add the above environment variables in Railway's **Variables** section.
3. Deploy – Railway will automatically build the Docker image.

## Local Development
```bash
pip install -r requirements.txt
export BOT_TOKEN=... API_ID=... API_HASH=... SESSION_STRING=...
python -m bot
```

---
*This bot is intended for educational purposes. Use responsibly and respect copyright laws.*