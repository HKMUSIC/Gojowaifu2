import asyncio
import importlib
from TEAMZYRO import ZYRO, application, LOGGER, send_start_message
from TEAMZYRO.modules import ALL_MODULES


async def main():
    # Load all modules
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("All modules loaded successfully.")

    # Start Pyrogram client
    await ZYRO.start()

    # -------------------------
    # START PTB 20.6 BOT SAFELY
    # -------------------------

    # step 1: initialize (does not close loop)
    await application.initialize()

    # step 2: start bot (async)
    await application.start()

    # step 3: start polling but NON-BLOCKING
    asyncio.create_task(application.updater.start_polling())

    # Send start message (optional)
    try:
        send_start_message()
    except Exception as e:
        LOGGER("START").error(f"Start message error: {e}")

    LOGGER("TEAMZYRO").info(
        "╔═════ஜ۩۞۩ஜ════╗\n  BOT RUNNING SUCCESSFULLY \n╚═════ஜ۩۞۩ஜ════╝"
    )

    # -------------------------------------
    # Prevent Heroku dyno from stopping
    # -------------------------------------
    while True:
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
