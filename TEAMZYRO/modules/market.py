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

markets_collection = db["market"]

# in-memory state
user_data = {}

# helper: Indian Sunday check (IST = UTC +5:30)
def is_ist_sunday():
    now_utc = datetime.utcnow()
    ist_now = now_utc + timedelta(hours=5, minutes=30)
    return ist_now.weekday() == 6  # Sunday

MARKET_TAG_IMAGES = [
    "https://files.catbox.moe/shslw1.jpg",
    "https://files.catbox.moe/syanmk.jpg",
    "https://files.catbox.moe/xokoit.jpg",
]

# /market command
@app.on_message(filters.command(["market", "hmarket", "hmarketmenu"]))
async def show_market(client, message):
    user_id = message.from_user.id

    if not is_ist_sunday():
        return await message.reply("*Market is closed. Opens every Sunday!*")

    characters_cursor = markets_collection.find()
    characters = await characters_cursor.to_list(length=None)

    if not characters:
        return await message.reply("🌌 The Market is empty! No rare waifus available right now.")

    current_index = 0
    character = characters[current_index]

    caption_message = (
        f"🌟 **Welcome to the Sunday Market!** 🌟\n\n"
        f"**Name:** {character.get('name')}\n"
        f"**Anime:** {character.get('anime')}\n"
        f"**Rarity:** {character.get('rarity')}\n"
        f"**Price:** {character.get('price')} Star Coins\n"
        f"**ID:** {character.get('id')}\n\n"
        "Use the buttons below to buy or browse previous/next waifus."
    )

    keyboard = [
        [
            InlineKeyboardButton("Prev", callback_data=f"market_prev_{current_index}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{current_index}"),
            InlineKeyboardButton("Next", callback_data=f"market_next_{current_index}"),
        ]
    ]

    try:
        if character.get("video_url"):
            await message.reply_video(
                video=character["video_url"],
                caption=caption_message,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await message.reply_photo(
                photo=character["img_url"],
                caption=caption_message,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
    except Exception as e:
        LOGGER.exception("Failed to send market media: %s", e)
        await message.reply(caption_message, reply_markup=InlineKeyboardMarkup(keyboard))

    user_data[user_id] = {"current_index": current_index}

# helper to edit market item
async def edit_market_item(message, character, caption_message, keyboard):
    try:
        if character.get("video_url"):
            await message.edit_media(
                InputMediaVideo(media=character["video_url"], caption=caption_message),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await message.edit_media(
                InputMediaPhoto(media=character["img_url"], caption=caption_message),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
    except Exception as e:
        try:
            # fallback to caption edit (if media exists)
            await message.edit_caption(
                caption=caption_message,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception:
            # final fallback for non-media messages
            await message.edit_text(
                text=caption_message,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        LOGGER.warning("edit_market_item fallback triggered: %s", e)

# callback: next
@app.on_callback_query(filters.regex(r"^market_next_\d+$"))
async def market_next(client, callback_query):
    user_id = callback_query.from_user.id
    passed_index = int(callback_query.data.split("_")[-1])

    characters = await markets_collection.find().to_list(length=None)
    if not characters:
        return await callback_query.answer("🌌 Market is empty!", show_alert=True)

    current_index = user_data.get(user_id, {}).get("current_index", passed_index)
    next_index = (current_index + 1) % len(characters)
    character = characters[next_index]

    caption_message = (
        f"🌟 **Sunday Market** 🌟\n\n"
        f"**Name:** {character.get('name')}\n"
        f"**Anime:** {character.get('anime')}\n"
        f"**Rarity:** {character.get('rarity')}\n"
        f"**Price:** {character.get('price')} Star Coins\n"
        f"**ID:** {character.get('id')}\n\n"
        "Use the buttons below to buy or browse."
    )

    keyboard = [
        [
            InlineKeyboardButton("Prev", callback_data=f"market_prev_{next_index}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{next_index}"),
            InlineKeyboardButton("Next", callback_data=f"market_next_{next_index}"),
        ]
    ]

    await edit_market_item(callback_query.message, character, caption_message, keyboard)
    user_data[user_id] = {"current_index": next_index}
    await callback_query.answer()

# callback: prev
@app.on_callback_query(filters.regex(r"^market_prev_\d+$"))
async def market_prev(client, callback_query):
    user_id = callback_query.from_user.id
    passed_index = int(callback_query.data.split("_")[-1])

    characters = await markets_collection.find().to_list(length=None)
    if not characters:
        return await callback_query.answer("🌌 Market is empty!", show_alert=True)

    current_index = user_data.get(user_id, {}).get("current_index", passed_index)
    prev_index = (current_index - 1) % len(characters)
    character = characters[prev_index]

    caption_message = (
        f"🌟 **Sunday Market** 🌟\n\n"
        f"**Name:** {character.get('name')}\n"
        f"**Anime:** {character.get('anime')}\n"
        f"**Rarity:** {character.get('rarity')}\n"
        f"**Price:** {character.get('price')} Star Coins\n"
        f"**ID:** {character.get('id')}\n\n"
        "Use the buttons below to buy or browse."
    )

    keyboard = [
        [
            InlineKeyboardButton("◀️ Prev", callback_data=f"market_prev_{prev_index}"),
            InlineKeyboardButton("ᴄʟᴀɪᴍ ɴᴏᴡ!", callback_data=f"market_buy_{prev_index}"),
            InlineKeyboardButton("Next ▶️", callback_data=f"market_next_{prev_index}"),
        ]
    ]

    await edit_market_item(callback_query.message, character, caption_message, keyboard)
    user_data[user_id] = {"current_index": prev_index}
    await callback_query.answer()

# callback: buy
@app.on_callback_query(filters.regex(r"^market_buy_\d+$"))
async def market_buy(client, callback_query):
    user_id = callback_query.from_user.id
    index = int(callback_query.data.split("_")[-1])

    if not is_ist_sunday():
        return await callback_query.answer("*Market is closed. Opens every Sunday!*", show_alert=True)

    characters = await markets_collection.find().to_list(length=None)
    if index >= len(characters):
        return await callback_query.answer("🚫 This waifu is no longer available!", show_alert=True)

    character = characters[index]
    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await callback_query.answer("🚫 You need to register first!", show_alert=True)

    price = int(character.get("price", 0))
    balance = int(user.get("balance", 0))

    if balance < price:
        return await callback_query.answer(
            f"🌠 You need {price - balance} more Star Coins to buy this waifu!", show_alert=True
        )

    new_balance = balance - price
    user_chars = user.get("characters", [])
    character_data = {
        "_id": ObjectId(),
        "img_url": character.get("img_url"),
        "video_url": character.get("video_url"),
        "name": character.get("name"),
        "anime": character.get("anime"),
        "rarity": character.get("rarity"),
        "id": character.get("id"),
    }
    user_chars.append(character_data)

    await user_collection.update_one(
        {"id": user_id}, {"$set": {"balance": new_balance, "characters": user_chars}}
    )

    tag_img = random.choice(MARKET_TAG_IMAGES)
    dm_text = (
        f"🎉 Congratulations! 🎉\n\n"
        f"You've just added **{character.get('name')}** (Rarity: {character.get('rarity')}) to your collection!\n\n"
        "Thank you for shopping at the Sunday Market. ✨"
    )

    dm_sent = True
    try:
        if character.get("video_url"):
            await client.send_video(chat_id=user_id, video=character["video_url"], caption=dm_text)
            await client.send_photo(chat_id=user_id, photo=tag_img, caption="ᴛʜᴀɴᴋꜱ ꜰᴏʀ ꜱʜᴏᴘᴘɪɴɢ ɪɴ ˹ 𝐆ᴏᴊᴏ ꭙ 𝐂ᴀᴛᴄʜᴇʀ ˼!")
        else:
            await client.send_photo(chat_id=user_id, photo=character.get("img_url"), caption=dm_text)
            await client.send_photo(chat_id=user_id, photo=tag_img, caption="ᴛʜᴀɴᴋꜱ ꜰᴏʀ ꜱʜᴏᴘᴘɪɴɢ ɪɴ ˹ 𝐆ᴏᴊᴏ ꭙ 𝐂ᴀᴛᴄʜᴇʀ ˼!")
    except Exception as e:
        LOGGER.warning("Failed to DM user after purchase: %s", e)
        dm_sent = False

    if dm_sent:
        await callback_query.answer("🎉 Purchase successful! Check your DM for details.")
        await callback_query.message.reply_text(
            f"🎉 {character.get('name')} has been added to <a href='tg://user?id={user_id}'>your collection</a>.",
            parse_mode="html",
        )
    else:
        await callback_query.answer("🎉 Purchased, but I couldn't DM you. Please /start the bot.", show_alert=True)
        await callback_query.message.reply_text(
            f"🎉 {character.get('name')} added to your collection. "
            "I couldn't DM you — please /start the bot so I can send the congratulations DM."
    )
        
# --- /madd command ---
@app.on_message(filters.command("madd") & filters.user(ADMIN_IDS))
async def add_market_item(client, message):
    try:
        args = message.text.split(maxsplit=3)
        if len(args) < 4:
            return await message.reply(
                "Usage: /madd [Name] [Rarity] [Price]\nExample: /madd Rem R 500\nReply to waifu photo/video!"
            )

        name = args[1]
        rarity = args[2]
        price = int(args[3])

        if message.reply_to_message:
            if message.reply_to_message.photo:
                img_url = await message.reply_to_message.photo.file_id
                video_url = None
            elif message.reply_to_message.video:
                video_url = await message.reply_to_message.video.file_id
                img_url = None
            else:
                return await message.reply("Please reply to a photo or video of the waifu!")
        else:
            return await message.reply("You must reply to a photo or video of the waifu!")

        waifu_id = str(uuid.uuid4())[:8]
        waifu_data = {
            "name": name,
            "rarity": rarity,
            "price": price,
            "img_url": img_url,
            "video_url": video_url,
            "id": waifu_id,
            "added_by": message.from_user.id,
        }

        await markets_collection.insert_one(waifu_data)

        await message.reply(
            f"✅ Character added successfully 🎉\n\n"
            f"**Name:** {name}\n"
            f"**Rarity:** {rarity}\n"
            f"**ID:** {waifu_id}\n"
            f"**Added by:** {message.from_user.first_name} ({message.from_user.id})",
            parse_mode="markdown"
        )
    except Exception as e:
        LOGGER.exception("Failed to add market waifu: %s", e)
        await message.reply(f"🚫 Failed to add waifu: {e}")


# --- /mupdate command ---
@app.on_message(filters.command("mupdate") & filters.user(ADMIN_IDS))
async def update_market_item(client, message):
    try:
        args = message.text.split(maxsplit=4)
        if len(args) < 5:
            return await message.reply(
                "Usage: /mupdate [WaifuID] [New Name] [New Rarity] [New Price]\nReply to new photo/video if updating media!"
            )

        waifu_id = args[1]
        new_name = args[2]
        new_rarity = args[3]
        new_price = int(args[4])

        update_data = {"name": new_name, "rarity": new_rarity, "price": new_price}

        if message.reply_to_message:
            if message.reply_to_message.photo:
                update_data["img_url"] = await message.reply_to_message.photo.file_id
                update_data["video_url"] = None
            elif message.reply_to_message.video:
                update_data["video_url"] = await message.reply_to_message.video.file_id
                update_data["img_url"] = None

        result = await markets_collection.find_one_and_update(
            {"id": waifu_id},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER
        )

        if not result:
            return await message.reply(f"🚫 No waifu found with ID {waifu_id}")

        await message.reply(
            f"✅ Character updated successfully 🎉\n\n"
            f"**Name:** {result['name']}\n"
            f"**Rarity:** {result['rarity']}\n"
            f"**ID:** {result['id']}",
            parse_mode="markdown"
        )
    except Exception as e:
        LOGGER.exception("Failed to update waifu: %s", e)
        await message.reply(f"🚫 Failed to update waifu: {e}")


# --- /mdelete command ---
@app.on_message(filters.command("mdelete") & filters.user(ADMIN_IDS))
async def delete_market_item(client, message):
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            return await message.reply("Usage: /mdelete [WaifuID]")

        waifu_id = args[1]

        result = await markets_collection.delete_one({"id": waifu_id})

        if result.deleted_count == 0:
            return await message.reply(f"🚫 No waifu found with ID {waifu_id}")

        await message.reply(f"✅ Waifu with ID {waifu_id} deleted successfully 🎉")
    except Exception as e:
        LOGGER.exception("Failed to delete waifu: %s", e)
        await message.reply(f"🚫 Failed to delete waifu: {e}")

