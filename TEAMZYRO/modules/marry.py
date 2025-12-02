from TEAMZYRO import app
from pyrogram import filters
from pyrogram.types import Message
import random
from pymongo import MongoClient

# MongoDB
client = MongoClient("mongodb+srv://Gojowaifu2:Gojowaifu2@cluster0.uvox90s.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["your_db"]
waifu_collection = db["waifus"]

@app.on_message(filters.command("marry"))
async def marry_cmd(client, message: Message):

    user = message.from_user.first_name

    # 1) Send Dice Like Screenshot
    dice_msg = await message.reply_dice("🎲")

    # 2) Fetch random waifu from MongoDB
    waifu = list(waifu_collection.aggregate([{"$sample": {"size": 1}}]))[0]

    name = waifu.get("name", "Unknown")
    rarity = waifu.get("rarity", "Unknown")
    anime = waifu.get("anime", "Unknown")
    image = waifu.get("image")

    # 3) Prepare caption like screenshot
    caption = f"""
CONGRATULATIONS! **{user}**, YOU ARE NOW MARRIED!
HERE IS YOUR CHARACTER:

**Name:** {name}
**Rarity:** {rarity}
**Anime:** {anime}
"""

    # 4) Send waifu image + caption
    if image:
        await message.reply_photo(image, caption=caption)
    else:
        await message.reply(caption)
