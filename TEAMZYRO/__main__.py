import asyncio
import logging
import importlib

from TEAMZYRO import ZYRO, LOGGER, config
from TEAMZYRO.modules import ALL_MODULES
from pyrogram import Client
from aiogram import Bot, Dispatcher

logging.basicConfig(level=logging.INFO)

# ---------------- Aiogram v3 setup ---------------- #

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# ------------- Pyrogram bot (your ZYRO alias) ------------- #

app = ZYRO  # ZYRO already = Client(...) in your __init__.py


# ------------------- LOAD MODULES ------------------- #

def load_modules():
    for module_name in ALL_MODULES:
        importlib.import_module("TEAMZYRO.modules." + module_name)

    LOGGER("TEAMZYRO.modules").info(
        "𝐀𝐥𝐥 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬 𝐋𝐨𝐚𝐝𝐞𝐝 𝐁𝐚𝐛𝐲🥳..."
    )


# ---------------------- STARTERS ---------------------- #

async def start_pyrogram():
    LOGGER("TEAMZYRO").info("Starting Pyrogram...")
    await app.start()
    await app.send_message(config.OWNER_ID, "Pyrogram Started ✔️")
    await app.idle()


async def start_aiogram():
    LOGGER("TEAMZYRO").info("Starting Aiogram...")
    await dp.start_polling(bot)


async def send_start_message():
    try:
        await app.send_message(config.OWNER_ID, "Bot Fully Online ✔️🥳")
    except Exception as e:
        LOGGER("TEAMZYRO").warning(f"Start message failed: {e}")


# ---------------------- MAIN ASYNC ---------------------- #

async def start_bot():
    load_modules()

    LOGGER("TEAMZYRO").info("Starting both bots...")

    await send_start_message()

    # Run aiogram + pyrogram parallel
    await asyncio.gather(
        start_aiogram(),
        start_pyrogram(),
    )


# ---------------------- MAIN ENTRY ---------------------- #

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
