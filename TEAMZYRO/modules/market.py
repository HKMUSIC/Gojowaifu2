import random
from bson import ObjectId
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from TEAMZYRO import *

market_collection = db["market"]
user_market_state = {}  # Track which user sees which waifu

# Rarity map
rarity_map = {
    1: "⚪️ Low",
    2: "🟠 Medium",
    3: "🔴 High",
    4: "🎩 Special Edition",
    5: "🪽 Elite Edition",
    6: "🪐 Exclusive",
    7: "💞 Valentine",
    8: "🎃 Halloween",
    9: "❄️ Winter",
    10: "🏖 Summer",
    11: "🎗 Royal",
    12: "💸 Luxury Edition",
    13: "🍃 echhi",
    14: "🌧️ Rainy Edition",
    15: "🎍 Festival"
}

# /market command
@app.on_message(filters.command("market"))
async def show_market(client, message):
    user_id = message.from_user.id

    # Fetch all market waifus
    characters_cursor = market_collection.find()
    characters = await characters_cursor.to_list(length=None)

    if not characters:
        return await message.reply("🌌 The Market is empty! No rare waifus available.")

    # Randomly pick 3 waifus
    characters_to_show = random.sample(characters, min(3, len(characters)))
    user_market_state[user_id] = {"characters": characters_to_show, "current_index": 0}

    await send_market_character(user_id, message, 0)


# Helper function to send market waifu
async def send_market_character(user_id, message_or_callback, index: int):
    state = user_market_state[user_id]
    characters = state["characters"]
    character = characters[index]

    # Use rarity map for display
    rarity_emoji = rarity_map.get(character.get("rarity_number", character.get("rarity", 1)), "⚪️ Low")
    price = character.get("price", 5000)

    caption_message = (
        f"🌟 **Rare Waifu Market!** 🌟\n\n"
        f"**Name:** {character['name']}\n"
        f"**Anime:** {character['anime']}\n"
        f"**Rarity:** {rarity_emoji}\n"
        f"**Price:** {price} coins\n\n"
        f"💎 Only the rarest waifus appear here!"
    )

    keyboard = [
        [
            InlineKeyboardButton("💰 Buy Now", callback_data=f"market_buy_{index}"),
            InlineKeyboardButton("➡ Next", callback_data="market_next")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(message_or_callback, "id"):  # message
        await message_or_callback.reply_photo(
            photo=character["img_url"],
            caption=caption_message,
            reply_markup=reply_markup
        )
    else:  # callback
        await message_or_callback.message.edit_media(
            media=InputMediaPhoto(media=character['img_url'], caption=caption_message),
            reply_markup=reply_markup
        )


# Buy waifu
@app.on_callback_query(filters.regex(r"market_buy_(\d+)"))
async def buy_market_character(client, cq):
    user_id = cq.from_user.id
    index = int(cq.matches[0].group(1))

    state = user_market_state.get(user_id)
    if not state:
        return await cq.answer("⚠ Market session expired! Use /market again.", show_alert=True)

    characters = state["characters"]
    if index >= len(characters):
        return await cq.answer("⚠ This waifu is no longer available!", show_alert=True)

    character = characters[index]

    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await cq.answer("🚫 You need to register first!", show_alert=True)
        return

    price = character.get("price", 5000)
    balance = user.get("balance", 0)

    if balance < price:
        return await cq.answer(f"💰 You need {price - balance} more coins to buy this waifu!", show_alert=True)

    # Deduct balance and add waifu
    new_balance = balance - price
    character_data = {
        "_id": ObjectId(),
        "img_url": character["img_url"],
        "name": character["name"],
        "anime": character["anime"],
        "rarity": character.get("rarity_number", 1),
        "id": character.get("id")
    }

    user_chars = user.get("characters", [])
    user_chars.append(character_data)
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"balance": new_balance, "characters": user_chars}}
    )

    await cq.answer(f"🎉 Waifu purchased! New Balance: {new_balance} coins", show_alert=True)


# Next waifu
@app.on_callback_query(filters.regex(r"market_next"))
async def next_market(client, cq):
    user_id = cq.from_user.id
    state = user_market_state.get(user_id)
    if not state:
        return await cq.answer("⚠ Market session expired! Use /market again.", show_alert=True)

    current_index = state["current_index"]
    next_index = (current_index + 1) % len(state["characters"])
    state["current_index"] = next_index

    await send_market_character(user_id, cq, next_index)
    await cq.answer()


# Admin add to market
@app.on_message(filters.command("addmarket"))
@require_power("add_market")
async def add_to_market(client, message):
    args = message.text.split()[1:]

    if len(args) != 2:
        return await message.reply("🌌 Usage: /addmarket <character-id> <price>")

    character_id, price = args
    try:
        price = int(price)
    except ValueError:
        return await message.reply("🚫 Price must be a number!")

    character = await collection.find_one({"id": character_id})
    if not character:
        return await message.reply("🚫 This waifu doesn't exist!")

    # Ensure rarity_number exists and is int
    rarity_number = int(character.get("rarity_number", 1))
    character["rarity_number"] = rarity_number
    character["price"] = price

    await market_collection.insert_one(character)
    await message.reply(f"🎉 {character['name']} added to the Market for {price} coins! Rarity: {rarity_map.get(rarity_number)}")
    
