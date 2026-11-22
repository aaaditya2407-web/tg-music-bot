async def main():
    global call_py, vc_ready
    from pyrogram import idle
    await bot.start()
    me = await bot.get_me()
    print(f"BOT USERNAME: @{me.username}", flush=True)

    try:
        from pytgcalls import PyTgCalls
        assistant = Client("assistant", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION, in_memory=True)
        call_py = PyTgCalls(assistant)

        @call_py.on_update()
        async def end_h(_, update):
            if type(update).__name__ == "StreamAudioEnded":
                if queues[update.chat_id]:
                    queues[update.chat_id].pop(0)
                await play_next(update.chat_id)

        await call_py.start()
        vc_ready = True
        print("Voice Chat Engine Ready!", flush=True)
    except Exception as e:
        print(f"VC Engine Error: {e}", flush=True)

    await idle()

if __name__ == "__main__":
    bot.run(main())
    
