import asyncio
import importlib
from TEAMZYRO import ZYRO, application, LOGGER, send_start_message
from TEAMZYRO.modules import ALL_MODULES


async def start_ptb():
    """PTB polling in background without blocking."""
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    LOGGER("PTB").info("PTB polling started")


async def safe_start_message():
    """Wrapper to safely call send_start_message() whether it is async or not."""
    try:
        result = send_start_message()

        if asyncio.iscoroutine(result):
            await result

    except Exception as e:
        LOGGER("START").error(f"Failed to send start message: {e}")


async def main():

    # Load modules
    for module in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module)

    LOGGER("TEAMZYRO.modules").info("All modules loaded")

    # Start Pyrogram
    await ZYRO.start()
    LOGGER("PYROGRAM").info("Pyrogram started")

    # Start PTB
    asyncio.create_task(start_ptb())

    # Safe Start Message
    await safe_start_message()

    LOGGER("TEAMZYRO").info("BOT RUNNING SUCCESSFULLY")

    # Keep bot alive
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
