from TEAMZYRO import *
import importlib
import logging
import asyncio
from TEAMZYRO.modules import ALL_MODULES


async def shutdown():
    """Cleanly cancel all running asyncio tasks to avoid Heroku crashes."""
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    for task in tasks:
        task.cancel()
        try:
            await task
        except:
            pass


def main() -> None:
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info("𝐀𝐥𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 𝐋𝐨𝐚𝐝𝐞𝐝 𝐁𝐚𝐛𝐲🥳...")

    try:
        # --- START BOTH BOTS SAFELY ---
        ZYRO.start()                                     # Pyrogram bot
        application.run_polling(drop_pending_updates=True)  # Aiogram bot
        send_start_message()

    finally:
        # --- SAFE SHUTDOWN (Fixes Task Destroyed Error) ---
        asyncio.run(shutdown())

    LOGGER("TEAMZYRO").info(
        "╔═════ஜ۩۞۩ஜ════╗\n  ☠︎︎MADE BY GOJOXNETWORK☠︎︎\n╚═════ஜ۩۞۩ஜ════╝"
    )


if __name__ == "__main__":
    main()
