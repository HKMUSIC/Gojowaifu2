import asyncio
import importlib
from TEAMZYRO import ZYRO, application, LOGGER, send_start_message
from TEAMZYRO.modules import ALL_MODULES


async def start_ptb():
    """Runs PTB in a background task without blocking the event loop."""
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    LOGGER("PTB").info("PTB polling started")


async def main():

    # Load modules
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("All modules loaded")

    # Start Pyrogram
    await ZYRO.start()
    LOGGER("PYROGRAM").info("Pyrogram started")

    # Start PTB in background
    asyncio.create_task(start_ptb())

    # Send start message
    try:
        await send_start_message()
    except Exception as e:
        LOGGER("START").error(f"Failed to send start message: {e}")

    LOGGER("TEAMZYRO").info("BOT RUNNING SUCCESSFULLY")

    # Keep alive forever
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
