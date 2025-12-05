import asyncio
import importlib
from TEAMZYRO import ZYRO, application, LOGGER
from TEAMZYRO.modules import ALL_MODULES


async def start_ptb():
    """Start PTB safely in background"""
    await application.initialize()
    await application.start()

    # Non-blocking polling
    asyncio.create_task(application.updater.start_polling())

    LOGGER("PTB").info("PTB polling started successfully.")


async def main():
    # Load all modules first
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("All modules loaded successfully.")

    # Start Pyrogram
    await ZYRO.start()
    LOGGER("PYROGRAM").info("Pyrogram started successfully.")

    # Start PTB in background task
    await start_ptb()

    LOGGER("TEAMZYRO").info(
        "╔═════ஜ۩۞۩ஜ════╗\n BOT RUNNING SUCCESSFULLY\n╚═════ஜ۩۞۩ஜ════╝"
    )

    # Keep alive forever
    while True:
        await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
