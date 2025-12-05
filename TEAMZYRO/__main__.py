import asyncio
import importlib
from TEAMZYRO import ZYRO, application, LOGGER, send_start_message
from TEAMZYRO.modules import ALL_MODULES


async def start_ptb():
    await application.initialize()
    await application.start()
    asyncio.create_task(application.updater.start_polling())
    LOGGER("PTB").info("Polling started")


async def main():
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("All modules loaded")

    # Start Pyrogram properly
    await ZYRO.start()

    # Start PTB in background
    await start_ptb()

    # Optional start msg
    try:
        send_start_message()
    except Exception as e:
        LOGGER("START").error(f"Start message error: {e}")

    LOGGER("TEAMZYRO").info("BOT RUNNING SUCCESSFULLY")

    # Keep alive
    while True:
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
