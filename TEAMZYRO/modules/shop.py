import urllib.request
import uuid
import requests
import random
import html
import logging
from pymongo import ReturnDocument
from typing import List
from bson import ObjectId
from datetime import datetime, timedelta
import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
)
from motor.motor_asyncio import AsyncIOMotorClient

from TEAMZYRO import *

market_collection = db["market"]
user_data = {}

async def get_user_data(user_id):
    return await user_collection.find_one({"id": user_id})

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)

###############################################
# MEDIA DETECTION
###############################################

def get_media_type(url: str):
    video_ext = ["mp4", "mov", "mkv", "webm"]
    if any(url.lower().endswith(ext) for ext in video_ext):
        return "video"
    return "photo"

###############################################
# CAPTION
###############################################

def build_caption(character):
    return f"""
✨ **Cosmic Premium Market** ✨

**🧬 Hero:** `{character['name']}`
**🌌 Realm:** `{character['anime']}`
**💠 Tier:** `{character['rarity']}`
**💰 Price:** `{character['price']}` Star Coins
**🆔 ID:** `{character['id']}`

⚡ *Discover Legends | Unlock Power | Build Your Army* ⚡
"""

###############################################
# BUTTONS
###############################################

def build_buttons(index):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Claim Legend", callback_data=f"buy_{index}")],
        [InlineKeyboardButton("➡ Next", callback_data="next")]
    ])

###############################################
# SHOW SHOP
###############################################

@app.on_message(filters.command(["shop", "market", "hshop", "hshopmenu"]))
async def show_shop(client, message):
    user_id = message.from_user.id
    characters = await shops_collection.find().to_list(length=None)

    if not characters:
        return await message.reply("🚫 Market is empty! Add characters first.")

    index = 0
    ch = characters[index]

    caption = build_caption(ch)
    buttons = build_buttons(index)
    media = get_media_type(ch['img_url'])

    if media == "video":
        await message.reply_video(video=ch['img_url'], caption=caption, reply_markup=buttons)
    else:
        await message.reply_photo(photo=ch['img_url'], caption=caption, reply_markup=buttons)

    user_data[user_id] = {"current_index": index}

###############################################
# BUY CHARACTER
###############################################

@app.on_callback_query(filters.regex("^buy_[0-9]+$"))
async def buy_character(client, query):
    user_id = query.from_user.id
    index = int(query.data.split("_")[1])

    characters = await shops_collection.find().to_list(length=None)
    if index >= len(characters):
        return await query.answer("❌ Character not found!", show_alert=True)

    ch = characters[index]
    user = await user_collection.find_one({"id": user_id})

    if not user:
        return await query.answer("❌ Please register first!", show_alert=True)

    price = ch['price']
    bal = user.get("balance", 0)

    if bal < price:
        return await query.answer(f"You need {price - bal} more coins!", show_alert=True)

    new_bal = bal - price

    owned = {
        "_id": ObjectId(),
        "id": ch["id"],
        "name": ch["name"],
        "anime": ch["anime"],
        "rarity": ch["rarity"],
        "img_url": ch["img_url"]
    }

    user["characters"].append(owned)

    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"balance": new_bal, "characters": user["characters"]}}
    )

    return await query.answer("🎉 Purchased! Enjoy your new legend!", show_alert=True)

###############################################
# NEXT ITEM
###############################################

@app.on_callback_query(filters.regex("^next$"))
async def next_item(client, query):
    user_id = query.from_user.id
    characters = await shops_collection.find().to_list(length=None)

    if not characters:
        return await query.answer("Empty market!", show_alert=True)

    state = user_data.get(user_id, {"current_index": 0})
    next_index = (state["current_index"] + 1) % len(characters)

    ch = characters[next_index]
    caption = build_caption(ch)
    buttons = build_buttons(next_index)
    media = get_media_type(ch['img_url'])

    try:
        if media == "video":
            await query.message.edit_media(InputMediaVideo(media=ch['img_url'], caption=caption), reply_markup=buttons)
        else:
            await query.message.edit_media(InputMediaPhoto(media=ch['img_url'], caption=caption), reply_markup=buttons)
    except Exception as e:
        return await query.answer(str(e), show_alert=True)

    user_data[user_id]["current_index"] = next_index
    await query.answer()

###############################################
# ADD TO SHOP
###############################################

@app.on_message(filters.command("addshop"))
@require_power("add_character")
async def add_to_shop(client, message):
    args = message.text.split()[1:]

    if len(args) != 2:
        return await message.reply("Usage: /addshop <id> <price>")

    cid, price = args
    try:
        price = int(price)
    except:
        return await message.reply("Price must be a number!")

    ch = await collection.find_one({"id": cid})
    if not ch:
        return await message.reply("Character not found!")

    ch["price"] = price
    await shops_collection.insert_one(ch)

    await message.reply(f"Added {ch['name']} for {price} coins!")


