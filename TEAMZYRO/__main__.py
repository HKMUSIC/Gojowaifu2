import asyncio
import importlib
import signal
import time

from TEAMZYRO import ZYRO, application, LOGGER
from TEAMZYRO.modules import ALL_MODULES
from pyrogram.errors import FloodWait


# -----------------------------------------------------
# GRACEFUL SHUTDOWN
# -----------------------------------------------------
async def shutdown():
    LOGGER("TEAMZYRO").info("Shutting down cleanly...")

    # Stop Aiogram
    try:
        await application.stop()
    except:
        pass

    try:
        await application.shutdown()
    except:
        pass

    # Stop Pyrogram
    try:
        await ZYRO.stop()
    except:
        pass

    # Cancel background tasks
    current = asyncio.current_task()
    tasks = [t for t in asyncio.all_tasks() if t is not current]

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    LOGGER("TEAMZYRO").info("Shutdown complete.")


# -----------------------------------------------------
# BOT STARTUP
# -----------------------------------------------------
async def start_bot():
    # Load all modules
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("𝐀𝐥𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 𝐋𝐨𝐚𝐝𝐞𝐝 𝐁𝐚𝐛𝐲🥳...")

    # -----------------------------------------------
    # SAFE PYROGRAM START WITH FLOODWAIT HANDLING
    # -----------------------------------------------
    while True:
        try:
            await ZYRO.start()
            break
        except FloodWait as e:
            LOGGER("TEAMZYRO").warning(f"FloodWait: waiting {e.value} seconds...")
            time.sleep(e.value)

    # -----------------------------------------------
    # CORRECT AIROGRAM / PTB STARTUP ORDER
    # -----------------------------------------------
    await application.initialize()     # MUST COME FIRST
    await application.start()          # THEN START
    LOGGER("TEAMZYRO").info("Aiogram started.")

    # -----------------------------------------------
    # START POLLING
    # -----------------------------------------------
    LOGGER("TEAMZYRO").info("Both bots started. Polling...")
    await application.start_polling()  # Runs forever


# -----------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------
def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Graceful shutdown handlers
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
