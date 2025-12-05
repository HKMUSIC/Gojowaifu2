import asyncio
import importlib
from TEAMZYRO import ZYRO, LOGGER, send_start_message
from TEAMZYRO.modules import ALL_MODULES


async def main():

    # Load all modules
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("All modules loaded")

    # Start Pyrogram client
    await ZYRO.start()

    # Send start message (ignore errors)
    try:
        send_start_message()
    except Exception as e:
        LOGGER("START").error(f"Start message error: {e}")

    LOGGER("TEAMZYRO").info("BOT RUNNING...")

    # Idle (keep receiving updates)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
