import asyncio
import importlib
import signal
from TEAMZYRO import ZYRO, application, LOGGER
from TEAMZYRO.modules import ALL_MODULES


# ---------------------------------------------
# GRACEFUL SHUTDOWN HANDLER
# ---------------------------------------------
async def shutdown():
    LOGGER("TEAMZYRO").info("Shutting down cleanly...")

    # --- Stop python-telegram-bot (PTB) ---
    try:
        await application.updater.stop()
    except:
        pass
    try:
        await application.stop()
    except:
        pass

    # --- Stop Pyrogram ---
    try:
        await ZYRO.stop()
    except:
        pass

    # Cancel pending asyncio tasks
    current = asyncio.current_task()
    tasks = [t for t in asyncio.all_tasks() if t is not current]

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    LOGGER("TEAMZYRO").info("Shutdown complete.")


# ---------------------------------------------
# MAIN BOT STARTER
# ---------------------------------------------
async def start_bot():
    # Load modules
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("𝐀𝐥𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 𝐋𝐨𝐚𝐝𝐞𝐝 𝐁𝐚𝐛𝐲🥳...")

    # --- Start PYROGRAM ---
    await ZYRO.start()

    # --- PTB INITIALIZE FIRST ---
    await application.initialize()

    # --- Then start PTB ---
    await application.start()

    # --- Start polling (non-blocking) ---
    await application.updater.start_polling()

    LOGGER("TEAMZYRO").info("Both bots started successfully and polling...")


# ---------------------------------------------
# ENTRYPOINT
# ---------------------------------------------
def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Heroku SIGTERM/SIGINT shutdown handler
    try:
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(shutdown()))
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(shutdown()))
    except:
        pass

    try:
        loop.run_until_complete(start_bot())
    finally:
        loop.run_until_complete(shutdown())
        loop.close()


if __name__ == "__main__":
    main()
