# bot.py
"""Telegram Group Voice Chat Music Bot
Features: /play, /vplay, /pause, /resume, /skip, /stop, /queue with inline buttons.
Uses: Pyrogram, PyTgCalls, yt-dlp, ffmpeg.
Environment variables: API_ID, API_HASH, BOT_TOKEN, STRING_SESSION.
"""

import os
import asyncio
import logging
from collections import deque
from typing import Deque, Dict

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pytgcalls import PyTgCalls, idle
from pytgcalls.exceptions import GroupCallNotFoundError
from pytgcalls.types import Update
from pytgcalls.types.input_stream import InputAudioStream
from yt_dlp import YoutubeDL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
STRING_SESSION = os.getenv("STRING_SESSION")

if not all([API_ID, API_HASH, BOT_TOKEN, STRING_SESSION]):
    raise RuntimeError("Missing required environment variables.")

# Pyrogram client (userbot for voice)
user = Client("user", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)
# Bot client for commands
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# PyTgCalls instance (attached to user client)
call = PyTgCalls(user)

# Simple in‑memory queue per chat_id
queues: Dict[int, Deque[Dict]] = {}

YDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
    "geo_bypass": True,
    "nocheckcertificate": True,
    "cachedir": False,
}

# Helper to extract info & download audio URL
async def get_audio(url: str) -> dict:
    loop = asyncio.get_event_loop()
    def _download():
        with YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            # Prefer direct audio URL
            if "url" not in info:
                # If it's a playlist entry, fetch real info
                info = ydl.extract_info(info["webpage_url"], download=False)
            return {
                "title": info.get("title"),
                "thumb": info.get("thumbnail"),
                "duration": info.get("duration"),
                "url": info.get("url"),
                "webpage_url": info.get("webpage_url"),
            }
    return await loop.run_in_executor(None, _download)

# Inline keyboard for controls
def control_kb(chat_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Pause", callback_data=f"pause|{chat_id}"),
            InlineKeyboardButton("▶️ Resume", callback_data=f"resume|{chat_id}"),
        ],
        [
            InlineKeyboardButton("⏭ Skip", callback_data=f"skip|{chat_id}"),
            InlineKeyboardButton("⏹ Stop", callback_data=f"stop|{chat_id}"),
        ],
    ])

async def start_next(chat_id: int):
    if not queues.get(chat_id):
        await call.leave_group_call(chat_id)
        return
    track = queues[chat_id][0]
    await call.change_stream(
        chat_id,
        InputAudioStream(
            track["url"],
            duration=track["duration"]
        ),
    )
    # Edit message with new track info
    await bot.send_photo(
        chat_id,
        photo=track["thumb"] or "",
        caption=f"▶️ **Now Playing:** [{track['title']}]({track['webpage_url']})",
        reply_markup=control_kb(chat_id),
    )

@bot.on_message(filters.command(["play", "vplay"]) & filters.group)
async def cmd_play(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: /play <song name or URL>")
        return
    query = " ".join(message.command[1:])
    await message.reply("🔎 Searching…")
    info = await get_audio(query)
    chat_id = message.chat.id
    # Init queue
    if chat_id not in queues:
        queues[chat_id] = deque()
    queues[chat_id].append(info)
    await message.reply(f"✅ Added to queue: [{info['title']}]({info['webpage_url']})", disable_web_page_preview=True)
    # Join call if not already
    try:
        await call.get_group_call(chat_id)
    except GroupCallNotFoundError:
        await call.join_group_call(chat_id, InputAudioStream(info["url"]))
        await bot.send_photo(
            chat_id,
            photo=info["thumb"] or "",
            caption=f"▶️ **Now Playing:** [{info['title']}]({info['webpage_url']})",
            reply_markup=control_kb(chat_id),
        )
        return
    # If already playing, do nothing – next track will be handled on skip/finish

@bot.on_message(filters.command("skip") & filters.group)
async def cmd_skip(client: Client, message: Message):
    chat_id = message.chat.id
    if not queues.get(chat_id):
        await message.reply("Queue is empty.")
        return
    # Remove current
    queues[chat_id].popleft()
    if queues[chat_id]:
        await start_next(chat_id)
        await message.reply("⏭ Skipped to next track.")
    else:
        await call.leave_group_call(chat_id)
        await message.reply("⏹ Stopped playback – queue empty.")

@bot.on_message(filters.command("pause") & filters.group)
async def cmd_pause(client: Client, message: Message):
    chat_id = message.chat.id
    await call.pause_stream(chat_id)
    await message.reply("⏸ Paused.")

@bot.on_message(filters.command("resume") & filters.group)
async def cmd_resume(client: Client, message: Message):
    chat_id = message.chat.id
    await call.resume_stream(chat_id)
    await message.reply("▶️ Resumed.")

@bot.on_message(filters.command("stop") & filters.group)
async def cmd_stop(client: Client, message: Message):
    chat_id = message.chat.id
    queues.pop(chat_id, None)
    await call.leave_group_call(chat_id)
    await message.reply("⏹ Stopped and cleared queue.")

@bot.on_message(filters.command("queue") & filters.group)
async def cmd_queue(client: Client, message: Message):
    chat_id = message.chat.id
    q = queues.get(chat_id)
    if not q:
        await message.reply("Queue is empty.")
        return
    text = "**Queue:**\n"
    for i, track in enumerate(list(q)):
        text += f"{i+1}. [{track['title']}]({track['webpage_url']})\n"
    await message.reply(text, disable_web_page_preview=True)

# Callback queries for inline buttons
@bot.on_callback_query()
async def cb_handler(client: Client, callback):
    data = callback.data.split("|")
    action, chat_id = data[0], int(data[1])
    if action == "pause":
        await call.pause_stream(chat_id)
        await callback.answer("Paused")
    elif action == "resume":
        await call.resume_stream(chat_id)
        await callback.answer("Resumed")
    elif action == "skip":
        if queues.get(chat_id):
            queues[chat_id].popleft()
            if queues[chat_id]:
                await start_next(chat_id)
                await callback.answer("Skipped")
            else:
                await call.leave_group_call(chat_id)
                await callback.answer("Stopped – empty queue")
        else:
            await callback.answer("Queue empty")
    elif action == "stop":
        queues.pop(chat_id, None)
        await call.leave_group_call(chat_id)
        await callback.answer("Stopped")

# Auto‑advance when a track ends
@call.on_stream_end()
async def on_stream_end(update: Update):
    chat_id = update.chat_id
    if queues.get(chat_id):
        queues[chat_id].popleft()
        if queues[chat_id]:
            await start_next(chat_id)
        else:
            await call.leave_group_call(chat_id)

async def main():
    await user.start()
    await bot.start()
    await call.start()
    logger.info("Bot is up and running.")
    await idle()
    await call.stop()
    await bot.stop()
    await user.stop()

if __name__ == "__main__":
    asyncio.run(main())
