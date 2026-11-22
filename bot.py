import os
import logging
import asyncio
from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from pytgcalls import PyTgCalls, idle
from pytgcalls.types.input_stream import InputAudioStream
from pytgcalls.types import Update as CallUpdate

import yt_dlp

# -------------------- Config --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable not set")

# Set to False if you want everyone to use the commands
ADMIN_ONLY = True

# -------------------- Logging --------------------
logging.basicConfig(
    format="[%(asctime)s] %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# -------------------- Queue Structure --------------------
class MusicQueue:
    def __init__(self):
        self._queue: List[dict] = []
        self.current = None

    def add(self, url: str, title: str, chat_id: int):
        self._queue.append({"url": url, "title": title, "chat_id": chat_id})

    def pop_next(self):
        if self._queue:
            self.current = self._queue.pop(0)
            return self.current
        self.current = None
        return None

    def clear(self):
        self._queue.clear()
        self.current = None

    def list(self):
        return self._queue

music_queues = {}

# -------------------- YouTube Helper --------------------
YDL_OPTIONS = {
    "format": "bestaudio",
    "noplaylist": True,
    "quiet": True,
    "extract_flat": "in_playlist",
    "default_search": "ytsearch",
}

async def get_yt_info(query: str):
    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
    if "entries" in info:
        info = info["entries"][0]
    return info["webpage_url"], info.get("title", "Unknown")

# -------------------- Bot Handlers --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎧 Welcome! Use /play <song name or YouTube URL> to start streaming."
    )

def is_user_admin(update: Update) -> bool:
    if not ADMIN_ONLY:
        return True
    user = update.effective_user
    chat = update.effective_chat
    member = chat.get_member(user.id)
    return member.status in ["creator", "administrator"]

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_admin(update):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not context.args:
        await update.message.reply_text("❗ Usage: /play <search term or YouTube URL>")
        return
    query = " ".join(context.args)
    chat_id = update.effective_chat.id

    await update.message.reply_text("🔎 Searching…")
    try:
        url, title = await get_yt_info(query)
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("❌ Could not retrieve video.")
        return

    queue = music_queues.setdefault(chat_id, MusicQueue())
    queue.add(url, title, chat_id)
    await update.message.reply_text(f"✅ Queued: {title}")

    # If nothing is playing, start playback
    if not queue.current:
        await start_playback(chat_id, context)

async def start_playback(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    queue = music_queues.get(chat_id)
    if not queue:
        return
    next_track = queue.pop_next()
    if not next_track:
        await context.bot.send_message(chat_id, "🛑 Queue empty. Leaving voice chat.")
        await leave_vc(chat_id)
        return
    url = next_track["url"]
    title = next_track["title"]
    await context.bot.send_message(chat_id, f"▶️ Now playing: {title}")

    # Join voice chat if not already joined
    if chat_id not in vc_clients:
        await vc_clients[chat_id].join_group_call(
            chat_id,
            InputAudioStream(
                url,
                audio_parameters=vc_clients[chat_id].default_audio_parameters,
            ),
        )
    else:
        await vc_clients[chat_id].change_stream(
            chat_id,
            InputAudioStream(
                url,
                audio_parameters=vc_clients[chat_id].default_audio_parameters,
            ),
        )

async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_admin(update):
        await update.message.reply_text("❌ Only admins can skip.")
        return
    chat_id = update.effective_chat.id
    queue = music_queues.get(chat_id)
    if not queue:
        await update.message.reply_text("❗ No active queue.")
        return
    await update.message.reply_text("⏭ Skipping…")
    await start_playback(chat_id, context)

async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_admin(update):
        await update.message.reply_text("❌ Only admins can pause.")
        return
    chat_id = update.effective_chat.id
    client = vc_clients.get(chat_id)
    if client:
        await client.pause_stream(chat_id)
        await update.message.reply_text("⏸ Paused.")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_admin(update):
        await update.message.reply_text("❌ Only admins can resume.")
        return
    chat_id = update.effective_chat.id
    client = vc_clients.get(chat_id)
    if client:
        await client.resume_stream(chat_id)
        await update.message.reply_text("▶️ Resumed.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_admin(update):
        await update.message.reply_text("❌ Only admins can stop.")
        return
    chat_id = update.effective_chat.id
    await leave_vc(chat_id)
    music_queues.pop(chat_id, None)
    await update.message.reply_text("🛑 Stopped and left voice chat.")

async def queue_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    queue = music_queues.get(chat_id)
    if not queue or not queue.list():
        await update.message.reply_text("📭 Queue is empty.")
        return
    text = "📃 Current Queue:\n"
    for idx, item in enumerate(queue.list(), start=1):
        text += f"{idx}. {item['title']}\n"
    await update.message.reply_text(text)

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_admin(update):
        await update.message.reply_text("❌ Only admins can clear.")
        return
    chat_id = update.effective_chat.id
    queue = music_queues.get(chat_id)
    if queue:
        queue.clear()
    await update.message.reply_text("🗑 Queue cleared.")

# -------------------- Voice Chat Client Management --------------------
vc_clients = {}

async def get_client(chat_id: int):
    if chat_id not in vc_clients:
        client = PyTgCalls(app)
        vc_clients[chat_id] = client
        # Register end-of-stream callback
        @client.on_stream_end()
        async def on_stream_end(_, __, __):
            await start_playback(chat_id, app)
    return vc_clients[chat_id]

async def leave_vc(chat_id: int):
    client = vc_clients.get(chat_id)
    if client:
        await client.leave_group_call(chat_id)
        vc_clients.pop(chat_id, None)

# -------------------- Main --------------------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("play", play))
app.add_handler(CommandHandler("skip", skip))
app.add_handler(CommandHandler("pause", pause))
app.add_handler(CommandHandler("resume", resume))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(CommandHandler("queue", queue_cmd))
app.add_handler(CommandHandler("clear", clear))

async def main():
    await app.initialize()
    await app.start()
    logger.info("Bot started.")
    await idle()  # keep the bot running
    await app.stop()
    await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
