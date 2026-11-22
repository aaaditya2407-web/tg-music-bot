# Telegram Group Voice‑Chat Music Bot

A lightweight music streaming bot for Telegram groups built with **Pyrogram**, **PyTgCalls (v2)**, **yt‑dlp**, and **FFmpeg**. It runs inside Docker and can be deployed to Railway (or any container platform).

## Features
- `/play <query|url>` – search YouTube or use a direct link.
- Inline control buttons: Pause, Resume, Skip, Stop.
- `/queue` – view current playlist.
- Automatic thumbnail & link cards.
- Works with Python 3.12.

## Environment variables
| Variable | Description |
|----------|-------------|
| `API_ID` | Telegram API ID |
| `API_HASH` | Telegram API hash |
| `BOT_TOKEN` | Bot token from BotFather |
| `STRING_SESSION` | Optional user session string (required for voice‑chat control) |

## Deploy to Railway (quick)
1. Create a Railway project → **Deploy from Repo**.
2. Use the repo URL: `https://github.com/aaaditya2407-web/tg-music-bot`.
3. Add the four environment variables under **Settings → Variables**.
4. Click **Deploy** – Railway will build the Docker image and start the bot.
5. Add the bot to a group, give it *Admin → Manage Voice Chats* rights, and use `/play`.

---
*This repo is public – feel free to fork, modify, or open issues.*
