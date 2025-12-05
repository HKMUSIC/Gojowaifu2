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

    # Stop Aiogram
    try:
        await application.shutdown()
    except:
        pass

    # Stop Pyrogram
    try:
        await ZYRO.stop()
    except:
        pass

    # Cancel all asyncio tasks
    current = asyncio.current_task()
    tasks = [t for t in asyncio.all_tasks() if t is not current]

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    LOGGER("TEAMZYRO").info("Shutdown complete.")


# ---------------------------------------------
# MAIN APP
# ---------------------------------------------
async def start_bot():
    # Import all modules
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("𝐀𝐥𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 𝐋𝐨𝐚𝐝𝐞𝐝 𝐁𝐚𝐛𝐲🥳...")

    # Start Pyrogram
    await ZYRO.start()

    # Start Aiogram
    await application.start()
    await application.initialize()

    LOGGER("TEAMZYRO").info("Both bots started successfully.")

    # Run Aiogram polling FOREVER until stopped
    await application.start_polling()


# ---------------------------------------------
# ENTRYPOINT
# ---------------------------------------------
def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Gracefully handle Heroku stop signals
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
        except:
            pass

    try:
        loop.run_until_complete(start_bot())
    finally:
        loop.run_until_complete(shutdown())
        loop.close()


if __name__ == "__main__":
    main()
