from TEAMZYRO import *
import importlib
import logging
from TEAMZYRO.modules import ALL_MODULES
import asyncio


async def start_all():
    # Load modules
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("𝐀𝐥𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 𝐋𝐨𝐚𝐝𝐞𝐝 𝐁𝐚𝐛𝐲🥳...")

    # Start Pyrogram safely
    await ZYRO.start()

    # After pyrogram starts — send start message
    try:
        send_start_message()
    except:
        pass

    # Start Telegram Bot polling (run blocking in thread)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: application.run_polling(drop_pending_updates=True)
    )


def main():
    asyncio.run(start_all())


if __name__ == "__main__":
    main()
