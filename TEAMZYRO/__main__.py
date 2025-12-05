import asyncio
import importlib
from TEAMZYRO import ZYRO, application, LOGGER
from TEAMZYRO.modules import ALL_MODULES
from TEAMZYRO.helpers import send_start_message_async   # <-- async version

async def main():

    # Load all modules
    for module_name in ALL_MODULES:
        importlib.import_module(f"TEAMZYRO.modules.{module_name}")

    LOGGER("TEAMZYRO.modules").info("All modules loaded successfully.")

    # -----------------------
    # START PYROGRAM BOT
    # -----------------------
    await ZYRO.start()

    # -----------------------
    # START PTB (async)
    # -----------------------
    await application.initialize()
    await application.start()
    await application.updater.start_polling()  # SAFE in PTB 20.6

    # ------------------------
    # SEND START MESSAGE SAFE
    # ------------------------
    try:
        await send_start_message_async(ZYRO)
    except Exception as e:
        LOGGER("START").error(f"Start message error: {e}")

    LOGGER("TEAMZYRO").info(
        "╔═════ஜ۩۞۩ஜ════╗\n  BOT RUNNING SUCCESSFULLY \n╚═════ஜ۩۞۩ஜ════╝"
    )

    # Keep bot alive
    while True:
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
