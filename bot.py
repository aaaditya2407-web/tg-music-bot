import os
import asyncio
from pyrogram import Client, filters

print("STEP 1: Script started", flush=True)

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

print(f"STEP 2: Token loaded (starts with {BOT_TOKEN[:8]}...)", flush=True)

bot = Client("test_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

@bot.on_message(filters.command("start"))
async def start_cmd(_, message):
    print("STEP 4: /start received!", flush=True)
    await message.reply_text("Bot Zinda Hai! Ab music module jodenge.")

async def main():
    print("STEP 3: Connecting to Telegram...", flush=True)
    await bot.start()
    me = await bot.get_me()
    print(f"STEP 3.5: Connected as @{me.username}!", flush=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
    
