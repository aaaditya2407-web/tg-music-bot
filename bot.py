# bot.py – Telegram VC music bot (py-tgcalls v2)

import os
import asyncio
from datetime import datetime
from collections import defaultdict

from pyrogram import Client, filters
from pyrogram.types import (Message, InlineKeyboardMarkup,
                            InlineKeyboardButton, ChatPermissions)
from pyrogram.errors import PeerIdInvalid, ChatAdminRequired

from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.media import MediaStream
from pytgcalls.exceptions import GroupCallNotFoundError, NoActiveGroupCall

from yt_dlp import YoutubeDL
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
STRING_SESSION = os.getenv("STRING_SESSION")

# ---------- Pyrogram client ----------
app = Client("vc_music_bot", api_id=API_ID, api_hash=API_HASH,
             bot_token=BOT_TOKEN, session_string=STRING_SESSION)

# ---------- PyTgCalls instance ----------
vc = PyTgCalls(app)

# ---------- Simple in‑memory queue ----------
queue = defaultdict(list)   # chat_id -> list of track dicts

# ---------- yt‑dl options ----------
YDL_OPTS = {
    "format": "bestaudio",
    "quiet": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "extract_flat": "in_playlist",
    "geo_bypass": True,
    "skip_download": True,
    "forcejson": True,
}

ytdl = YoutubeDL(YDL_OPTS)

# ---------- Helper functions ----------

def extract_info(query: str) -> dict:
    """Return a dict with title, url, thumb, duration (seconds)."""
    info = ytdl.extract_info(query, download=False)
    if "entries" in info:
        # ytsearch returns a list inside 'entries'
        info = info["entries"][0]
    return {
        "title": info.get("title"),
        "url": info.get("url"),
        "webpage_url": info.get("webpage_url"),
        "thumb": info.get("thumbnail"),
        "duration": info.get("duration"),
    }

async def start_playback(chat_id: int):
    if not queue[chat_id]:
        return
    track = queue[chat_id][0]
    stream = MediaStream(track["url"])
    try:
        await vc.join_group_call(chat_id, stream)
    except Exception as e:
        # If a call already exists, replace the stream
        await vc.change_stream(chat_id, stream)
    await app.send_message(
        chat_id,
        f"▶️ **Now playing:** [{track['title']}]({track['webpage_url']})",
        reply_markup=control_markup(),
        disable_web_page_preview=False,
    )

def control_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Pause", callback_data="pause"),
            InlineKeyboardButton("▶️ Resume", callback_data="resume"),
        ],
        [
            InlineKeyboardButton("⏭ Skip", callback_data="skip"),
            InlineKeyboardButton("⏹ Stop", callback_data="stop"),
        ],
    ])

async def skip_track(chat_id: int):
    if queue[chat_id]:
        queue[chat_id].pop(0)  # remove current
    if queue[chat_id]:
        await start_playback(chat_id)
    else:
        await vc.leave_group_call(chat_id)
        await app.send_message(chat_id, "🛑 Queue is empty, left voice chat.")

# ---------- Command handlers ----------

@app.on_message(filters.command("play") & filters.group)
async def cmd_play(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /play <song name or URL>")
        return
    query = " ".join(message.command[1:])
    await message.reply("🔎 Searching…")
    track = extract_info(query)
    if not track:
        await message.reply("❌ Could not find the track.")
        return
    chat_id = message.chat.id
    queue[chat_id].append(track)
    if len(queue[chat_id]) == 1:
        await start_playback(chat_id)
    else:
        await message.reply(f"✅ Added to queue: [{track['title']}]({track['webpage_url']})", disable_web_page_preview=True)

@app.on_message(filters.command("vplay") & filters.private)
async def cmd_vplay(client: Client, message: Message):
    await message.reply("Use /play in a group to start streaming.")

@app.on_message(filters.command("pause") & filters.group)
async def cmd_pause(client: Client, message: Message):
    chat_id = message.chat.id
    try:
        await vc.pause_stream(chat_id)
        await message.reply("⏸ Paused.")
    except Exception:
        await message.reply("❗ No active stream to pause.")

@app.on_message(filters.command("resume") & filters.group)
async def cmd_resume(client: Client, message: Message):
    chat_id = message.chat.id
    try:
        await vc.resume_stream(chat_id)
        await message.reply("▶️ Resumed.")
    except Exception:
        await message.reply("❗ No paused stream.")

@app.on_message(filters.command("skip") & filters.group)
async def cmd_skip(client: Client, message: Message):
    await skip_track(message.chat.id)

@app.on_message(filters.command("stop") & filters.group)
async def cmd_stop(client: Client, message: Message):
    chat_id = message.chat.id
    queue[chat_id].clear()
    try:
        await vc.leave_group_call(chat_id)
        await message.reply("⏹ Stopped playback and cleared the queue.")
    except Exception:
        await message.reply("❗ Not in a voice call.")

@app.on_message(filters.command("queue") & filters.group)
async def cmd_queue(client: Client, message: Message):
    chat_id = message.chat.id
    if not queue[chat_id]:
        await message.reply("📭 Queue is empty.")
        return
    text = "📃 **Current Queue**\n"
    for i, track in enumerate(queue[chat_id], start=1):
        dur = str(datetime.utcfromtimestamp(track["duration"]).strftime('%M:%S')) if track["duration"] else "?"
        text += f"{i}. [{track['title']}]({track['webpage_url']}) `[{dur}]`\n"
    await message.reply(text, disable_web_page_preview=True)

# ---------- Callback query handling ----------

@app.on_callback_query()
async def cb_handler(client: Client, callback):
    data = callback.data
    chat_id = callback.message.chat.id
    if data == "pause":
        await vc.pause_stream(chat_id)
        await callback.answer("Paused", show_alert=False)
    elif data == "resume":
        await vc.resume_stream(chat_id)
        await callback.answer("Resumed", show_alert=False)
    elif data == "skip":
        await skip_track(chat_id)
        await callback.answer("Skipped", show_alert=False)
    elif data == "stop":
        queue[chat_id].clear()
        await vc.leave_group_call(chat_id)
        await callback.answer("Stopped", show_alert=False)
    else:
        await callback.answer("Unknown action", show_alert=False)

# ---------- Startup ----------

@app.on_startup
async def on_startup(client: Client):
    await vc.start()
    print("✅ Bot started and PyTgCalls ready")

@app.on_shutdown
async def on_shutdown(client: Client):
    await vc.stop()
    print("🛑 Bot stopped")

if __name__ == "__main__":
    print("🔧 Launching bot…")
    app.run()
