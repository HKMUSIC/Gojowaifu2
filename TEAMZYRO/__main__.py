import asyncio
import logging
import importlib

from TEAMZYRO import ZYRO, LOGGER
from TEAMZYRO import config
from TEAMZYRO.modules import ALL_MODULES

from aiogram import Bot, Dispatcher


logging.basicConfig(level=logging.INFO)

# -------- Aiogram Setup -------- #

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


# -------- Load All Modules -------- #

def load_modules():
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info(
        "𝐀𝐥𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 𝐋𝐨𝐚𝐝𝐞𝐝 𝐁𝐚𝐛𝐲🥳..."
    )


# -------- Pyrogram Start -------- #

async def start_pyrogram():
    LOGGER("TEAMZYRO").info("Starting Pyrogram...")
    await ZYRO.start()
    await ZYRO.send_message(config.OWNER_ID, "Pyrogram Started ✔️")
    await ZYRO.idle()


# -------- Aiogram Start -------- #

async def start_aiogram():
    LOGGER("TEAMZYRO").info("Starting Aiogram...")
    await dp.start_polling(bot)


# -------- Start message -------- #

async def start_msg():
    try:
        await ZYRO.send_message(config.OWNER_ID, "Bot Fully Online ✔️")
    except:
        pass


# -------- START BOT -------- #

async def start_bot():
    load_modules()
    await start_msg()

    LOGGER("TEAMZYRO").info("Both bots starting...")

    await asyncio.gather(
        start_aiogram(),
        start_pyrogram(),
    )


# -------- MAIN -------- #

def main():
    LOGGER("TEAMZYRO").info(
        "╔═════ஜ۩۞۩ஜ════╗\n  ☠︎︎MADE BY GOJOXNETWORK☠︎︎\n╚═════ஜ۩۞۩ஜ════╝"
    )

    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        LOGGER("TEAMZYRO").info("Shutting down cleanly...")
    except Exception as e:
        LOGGER("TEAMZYRO").error(f"Error: {e}")


if __name__ == "__main__":
    main()
