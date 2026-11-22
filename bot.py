    import os
import asyncio
from collections import defaultdict
import yt_dlp
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
STRING_SESSION = os.environ.get("STRING_SESSION", "").strip()

bot = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)
assistant = Client("assistant", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION, in_memory=True)
call_py = PyTgCalls(assistant)
queues = defaultdict(list)

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "extractor_args": {"youtube": {"player_client": ["android", "ios", "web"]}},
}

def get_audio_info(query: str):
    sources = [f"ytsearch1:{query}", f"scsearch1:{query}"] if not query.startswith("http") else [query]
    last_err = None
    for src in sources:
        try:
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                info = ydl.extract_info(src, download=False)
                if "entries" in info:
                    if not info["entries"]:
                        continue
                    info = info["entries"][0]
                return {
                    "title": info.get("title", "Unknown"),
                    "url": info["url"],
                    "webpage_url": info.get("webpage_url", src),
                }
        except Exception as e:
            last_err = e
    raise last_err

async def play_next(chat_id: int):
    if not queues[chat_id]:
        try:
            await call_py.leave_call(chat_id)
        except Exception:
            pass
        return
    track = queues[chat_id][0]
    try:
        await call_py.play(chat_id, MediaStream(track["url"], video_flags=MediaStream.Flags.IGNORE))
        await bot.send_message(chat_id, f"Now Playing: {track['title']}")
    except Exception as e:
        await bot.send_message(chat_id, f"Stream error: {e}")
        queues[chat_id].pop(0)
        await play_next(chat_id)

@bot.on_message(filters.command(["start", "help"]))
async def start_handler(_, m: Message):
    await m.reply_text("Music Bot Online!\nCommands: /play, /pause, /resume, /skip, /stop, /queue")

@bot.on_message(filters.command("play"))
async def play_handler(_, m: Message):
    if len(m.command) < 2:
        return await m.reply_text("Usage: /play <song name>")
    query = m.text.split(None, 1)[1]
    status = await m.reply_text(f"Searching: {query}...")
    try:
        track = await asyncio.to_thread(get_audio_info, query)
    except Exception as e:
        return await status.edit_text(f"Search failed: {e}")

    if m.chat.type.name == "PRIVATE":
        await status.edit_text(f"Downloading: {track['title']}...")
        ydl_dl = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": "/tmp/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "extractor_args": {"youtube": {"player_client": ["android", "ios", "web"]}},
        }
        def dl():
            with yt_dlp.YoutubeDL(ydl_dl) as ydl:
                info = ydl.extract_info(track["webpage_url"], download=True)
                if "entries" in info:
                    info = info["entries"][0]
                return ydl.prepare_filename(info), info.get("title", "Audio")
        try:
            fpath, title = await asyncio.to_thread(dl)
            await m.reply_audio(fpath, title=title)
            await status.delete()
            if os.path.exists(fpath):
                os.remove(fpath)
        except Exception as e:
            await status.edit_text(f"Download failed: {e}")
        return

    queues[m.chat.id].append(track)
    if len(queues[m.chat.id]) == 1:
        await status.delete()
        await play_next(m.chat.id)
    else:
        await status.edit_text(f"Queued (#{len(queues[m.chat.id])}): {track['title']}")

@bot.on_message(filters.command("pause") & filters.group)
async def pause_h(_, m: Message):
    try:
        await call_py.pause_stream(m.chat.id)
        await m.reply_text("Paused.")
    except Exception as e:
        await m.reply_text(f"Error: {e}")

@bot.on_message(filters.command("resume") & filters.group)
async def resume_h(_, m: Message):
    try:
        await call_py.resume_stream(m.chat.id)
        await m.reply_text("Resumed.")
    except Exception as e:
        await m.reply_text(f"Error: {e}")

@bot.on_message(filters.command("skip") & filters.group)
async def skip_h(_, m: Message):
    if queues[m.chat.id]:
        queues[m.chat.id].pop(0)
        await m.reply_text("Skipped.")
        await play_next(m.chat.id)

@bot.on_message(filters.command("stop") & filters.group)
async def stop_h(_, m: Message):
    queues[m.chat.id].clear()
    try:
        await call_py.leave_call(m.chat.id)
    except Exception:
        pass
    await m.reply_text("Stopped.")

@bot.on_message(filters.command("queue") & filters.group)
async def queue_h(_, m: Message):
    q = queues[m.chat.id]
    await m.reply_text("Queue:\n" + "\n".join(f"{i+1}. {t['title']}" for i, t in enumerate(q)) if q else "Queue is empty.")

@call_py.on_update()
async def end_h(_, update):
    if type(update).__name__ == "StreamAudioEnded":
        if queues[update.chat_id]:
            queues[update.chat_id].pop(0)
        await play_next(update.chat_id)

async def main():
    await call_py.start()
    print("Voice Chat Engine Ready!", flush=True)
    await bot.start()
    me = await bot.get_me()
    print(f"BOT USERNAME: @{me.username} is listening!", flush=True)
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
