import asyncio
import importlib
import logging

from TEAMZYRO import *
from TEAMZYRO.modules import ALL_MODULES


async def main() -> None:
    # Load all modules
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("𝐀𝐥𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 𝐋𝐨𝐚𝐝𝐞𝐝 𝐁𝐚𝐛𝐲🥳...")

    # Start Pyrogram Client
    await ZYRO.start()

    # Start Aiogram — NON BLOCKING
    asyncio.create_task(application.run_polling(drop_pending_updates=True))

    # Send start message (your function)
    try:
        send_start_message()
    except Exception as e:
        LOGGER("START").error(f"Start message error: {e}")

    LOGGER("TEAMZYRO").info(
        "╔═════ஜ۩۞۩ஜ════╗\n  ☠︎︎MADE BY GOJOXNETWORK☠︎︎\n╚═════ஜ۩۞۩ஜ════╝"
    )

    # Keep Heroku process alive forever
    while True:
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
