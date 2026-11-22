import os
import asyncio
import logging
from urllib.parse import urlparse, parse_qs

from telegram import Update, ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from pyrogram import Client
from pyrogram.types import ChatMemberUpdated

from pytgcalls import PyTgCalls
from pytgcalls.types import Update as TgCallsUpdate
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.types.stream import StreamAudioEnded

import yt_dlp

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Config ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
# ----------------------------

# Pyrogram client (user) for voice chat
user = Client("music_user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# PyTgCalls instance
pytgcalls = PyTgCalls(user)

# Simple queue per chat_id
queues = {}

# ---------- Helper Functions ----------
async def download_youtube(url: str) -> str:
    """Download audio using yt-dlp and return the file path."""
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # After post‑process, extension becomes .mp3
        base, _ = os.path.splitext(filename)
        return f"{base}.mp3"

def get_youtube_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        return parsed.path[1:]
    if parsed.hostname in ("youtube.com", "www.youtube.com", "m.youtube.com"):
        qs = parse_qs(parsed.query)
        return qs.get("v", [None])[0]
    return None

# ---------- Bot Commands ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I am a music bot. Use /join to enter voice chat, then /play <YouTube URL> to stream."
    )

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    try:
        await pytgcalls.join_group_call(
            chat.id,
            AudioPiped("input.raw"),  # placeholder, will be replaced when playing
        )
        await update.message.reply_text("Joined voice chat.")
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(f"Failed to join: {e}")

async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    try:
        await pytgcalls.leave_group_call(chat.id)
        await update.message.reply_text("Left voice chat.")
        queues.pop(chat.id, None)
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(f"Error leaving: {e}")

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /play <YouTube URL>")
        return
    url = context.args[0]
    yt_id = get_youtube_id(url)
    if not yt_id:
        await update.message.reply_text("Invalid YouTube URL.")
        return
    await update.message.reply_chat_action(ChatAction.RECORD_AUDIO)
    try:
        file_path = await download_youtube(url)
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text("Failed to download video.")
        return
    # Queue handling
    q = queues.setdefault(chat.id, [])
    q.append(file_path)
    await update.message.reply_text(f"Queued: {yt_id}")
    # If not already playing, start playback
    if len(q) == 1:
        await start_playback(chat.id)

async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await stop_current(chat.id)
    await update.message.reply_text("Skipped current track.")

# ---------- Playback Management ----------
async def start_playback(chat_id: int):
    if not queues.get(chat_id):
        return
    file_path = queues[chat_id][0]
    try:
        await pytgcalls.change_stream(chat_id, AudioPiped(file_path))
    except Exception as e:
        logger.exception(e)
        # If stream not started yet, join with the file
        await pytgcalls.join_group_call(chat_id, AudioPiped(file_path))

async def stop_current(chat_id: int):
    # Remove current track and start next if exists
    q = queues.get(chat_id)
    if not q:
        return
    q.pop(0)
    if q:
        await start_playback(chat_id)
    else:
        # No more tracks – leave voice chat
        try:
            await pytgcalls.leave_group_call(chat_id)
        except Exception:
            pass

# ---------- PyTgCalls Event Handlers ----------
@pytgcalls.on_stream_end()
async def on_stream_end_handler(_, update: TgCallsUpdate):
    chat_id = update.chat_id
    await stop_current(chat_id)

# ---------- Main ----------
async def main():
    # Ensure download folder exists
    os.makedirs("downloads", exist_ok=True)
    # Start Pyrogram client and PyTgCalls
    await user.start()
    await pytgcalls.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CommandHandler("skip", skip))
    app.add_handler(CommandHandler("stop", leave))

    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()  # keep running

if __name__ == "__main__":
    asyncio.run(main())
