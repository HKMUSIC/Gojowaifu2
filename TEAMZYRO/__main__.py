import asyncio
import importlib
from TEAMZYRO import *
from TEAMZYRO import ZYRO, application, LOGGER, send_start_message
from TEAMZYRO.modules import ALL_MODULES


async def run_ptb():
    """Run PTB polling in its own loop without blocking Pyrogram."""
    await application.initialize()
    await application.start()
    await application.updater.start_polling()   # NON-BLOCKING POLLING


async def main():

    # Load modules
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("All modules loaded")

    # Start Pyrogram bot
    await ZYRO.start()

    # Start PTB polling in separate task
    asyncio.create_task(run_ptb())

    # Send startup message
    try:
        await send_start_message()
    except Exception as e:
        LOGGER("START").error(f"Failed to send start message: {e}")

    LOGGER("TEAMZYRO").info("BOT RUNNING SUCCESSFULLY")

    # Keep alive
    while True:
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
