import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, List

from pyrogram import Client, filters
from pyrogram.types import (Message, InlineKeyboardMarkup,
                            InlineKeyboardButton, CallbackQuery)
from pyrogram.errors import ChatAdminRequired, UserNotParticipant

from pytgcalls import PyTgCalls, idle
from pytgcalls.types import AudioPiped
from pytgcalls.exceptions import NoActiveGroupCall

import yt_dlp
import ffmpeg
from dotenv import load_dotenv

# ------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
STRING_SESSION = os.getenv("STRING_SESSION")  # optional user session for voice chat control

# ------------------------------------------------------------
# Basic logging configuration
# ------------------------------------------------------------
logging.basicConfig(
    format="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ------------------------------------------------------------
# Pyrogram client (bot) and PyTgCalls instance
# ------------------------------------------------------------
app = Client("tg_music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
# If you provide a user String Session you can also control voice chat as a user.
# For simplicity we only use the bot account here.

tgcalls = PyTgCalls(app)

# ------------------------------------------------------------
# Simple in‑memory queue structure
# ------------------------------------------------------------
queues: Dict[int, List[Dict]] = {}

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------
YTDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
    "default_search": "ytsearch",
    "geo_bypass": True,
    "nocheckcertificate": True,
    "outtmpl": "downloads/%(id)s.%(ext)s",
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTS)

def download_audio(url: str) -> Path:
    """Download a YouTube/audio URL and return the path to the converted raw PCM file.
    The function returns a Path pointing to a .raw file suitable for AudioPiped.
    """
    info = ytdl.extract_info(url, download=False)
    # yt_dlp may return a playlist dict; we only need the first entry.
    if "entries" in info:
        info = info["entries"][0]
    title = info.get("title", "unknown")
    video_id = info.get("id")
    download_path = Path(f"downloads/{video_id}.webm")
    # Download the audio file
    ytdl.process_info(info)
    # Convert to raw PCM (s16le, 48kHz, stereo) for py‑tgcalls
    raw_path = Path(f"downloads/{video_id}.raw")
    if not raw_path.is_file():
        (
            ffmpeg
            .input(str(download_path))
            .output(str(raw_path), format="s16le", acodec="pcm_s16le", ac=2, ar="48000")
            .overwrite_output()
            .run(quiet=True)
        )
    return raw_path

def get_queue(chat_id: int) -> List[Dict]:
    return queues.setdefault(chat_id, [])

async def start_call(chat_id: int, audio_path: Path):
    try:
        await tgcalls.join_group_call(chat_id, AudioPiped(str(audio_path)))
    except NoActiveGroupCall:
        # No active group call – try to start one via the bot admin rights.
        await app.send_message(chat_id, "❗️ No active voice chat. Please start a voice chat first.")
    except Exception as e:
        log.exception(e)
        await app.send_message(chat_id, f"❗️ Failed to join voice chat: {e}")

async def play_next(chat_id: int):
    q = get_queue(chat_id)
    if not q:
        await tgcalls.leave_group_call(chat_id)
        return
    track = q.pop(0)
    await start_call(chat_id, track["path"])
    # Show now‑playing message with inline controls
    await app.send_photo(
        chat_id,
        photo=track["thumb"],
        caption=f"▶️ **Now playing:** [{track['title']}]({track['url']})",
        reply_markup=control_markup(chat_id),
    )

def control_markup(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏸ Pause", callback_data=f"pause|{chat_id}"),
                InlineKeyboardButton("▶️ Resume", callback_data=f"resume|{chat_id}"),
            ],
            [
                InlineKeyboardButton("⏭ Skip", callback_data=f"skip|{chat_id}"),
                InlineKeyboardButton("⏹ Stop", callback_data=f"stop|{chat_id}"),
            ],
        ]
    )

# ------------------------------------------------------------
# Command handlers
# ------------------------------------------------------------
@app.on_message(filters.command("play") & filters.group)
async def cmd_play(_: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.text:
        await message.reply("⚠️ Reply to a YouTube/URL or type `/play <url>`.")
        return
    query = message.text.split(maxsplit=1)[1] if len(message.command) > 1 else message.reply_to_message.text
    await message.reply("🔎 Searching…")
    try:
        path = download_audio(query)
        info = ytdl.extract_info(query, download=False)
        title = info.get("title", "unknown")
        thumb = info.get("thumbnail", "https://i.imgur.com/3M1u4b8.png")
        url = info.get("webpage_url", query)
        # Append to queue
        get_queue(message.chat.id).append({"title": title, "url": url, "thumb": thumb, "path": path})
        if not tgcalls.active_calls.get(message.chat.id):
            await play_next(message.chat.id)
        else:
            await message.reply(f"✅ **Queued:** [{title}]({url})", disable_web_page_preview=True)
    except Exception as e:
        log.exception(e)
        await message.reply(f"❌ Failed to process request: {e}")

@app.on_message(filters.command(["vplay", "playvc"]) & filters.group)
async def cmd_vplay(_: Client, message: Message):
    # Alias for /play – kept for compatibility with existing bots
    await cmd_play(_, message)

@app.on_callback_query(filters.regex(r"^(pause|resume|skip|stop)\|"))
async def cb_controls(_: Client, call: CallbackQuery):
    action, chat_id = call.data.split("|")
    chat_id = int(chat_id)
    if action == "pause":
        try:
            await tgcalls.pause_stream(chat_id)
            await call.answer("⏸ Paused", show_alert=False)
        except Exception as e:
            await call.answer(str(e), show_alert=True)
    elif action == "resume":
        try:
            await tgcalls.resume_stream(chat_id)
            await call.answer("▶️ Resumed", show_alert=False)
        except Exception as e:
            await call.answer(str(e), show_alert=True)
    elif action == "skip":
        await call.answer("⏭ Skipping…", show_alert=False)
        await play_next(chat_id)
    elif action == "stop":
        await tgcalls.leave_group_call(chat_id)
        get_queue(chat_id).clear()
        await call.message.delete()
        await call.answer("⏹ Stopped", show_alert=False)

@app.on_message(filters.command("queue") & filters.group)
async def cmd_queue(_: Client, message: Message):
    q = get_queue(message.chat.id)
    if not q:
        await message.reply("📭 Queue is empty.")
        return
    txt = "**Current Queue:**\n"
    for i, track in enumerate(q, start=1):
        txt += f"{i}. [{track['title']}]({track['url']})\n"
    await message.reply(txt, disable_web_page_preview=True)

# ------------------------------------------------------------
# Startup & shutdown
# ------------------------------------------------------------
@app.on_message(filters.command("start") & filters.private)
async def cmd_start(_: Client, message: Message):
    await message.reply(
        "👋 Hi! Add me to a group, give admin rights (manage voice chats) and use /play <url> to start streaming music.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("GitHub", url="https://github.com/aaaditya2407-web/tg-music-bot")]
        ]),
    )

@app.on_message(filters.command("stop") & filters.group)
async def cmd_stop(_: Client, message: Message):
    await tgcalls.leave_group_call(message.chat.id)
    get_queue(message.chat.id).clear()
    await message.reply("⏹ Stopped playback and cleared the queue.")

# ------------------------------------------------------------
# Run the bot
# ------------------------------------------------------------
async def main():
    await app.start()
    await tgcalls.start()
    log.info("Bot is ready.")
    await idle()
    await tgcalls.stop()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
