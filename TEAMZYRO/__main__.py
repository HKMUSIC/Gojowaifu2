import asyncio
import importlib
from TEAMZYRO import ZYRO, application, LOGGER, send_start_message
from TEAMZYRO.modules import ALL_MODULES


async def main():

    # Load all modules
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("All modules loaded")

    # Start Pyrogram bot
    await ZYRO.start()

    # Start PTB (Telegram Bot API)
    await application.initialize()
    await application.start()
    asyncio.create_task(application.updater.start_polling())

    # Start message
    try:
        send_start_message()
    except Exception as e:
        LOGGER("START").error(f"Failed to send start message: {e}")

    LOGGER("TEAMZYRO").info("BOT RUNNING SUCCESSFULLY")

    # Prevent exit forever
    while True:
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
