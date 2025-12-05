from TEAMZYRO import *
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    CallbackQuery,
    Message,
)
from itertools import groupby
import math
import random
import asyncio
from html import escape


# -------------------------------
# RARITY MAP
# -------------------------------

rarity_map = {
    "low": "⚪️ Low",
    "medium": "🟠 Medium",
    "high": "🔴 High",
    "special": "🎩 Special Edition",
    "elite": "🪽 Elite Edition",
    "exclusive": "🪐 Exclusive",
    "valentine": "💞 Valentine",
    "halloween": "🎃 Halloween",
    "winter": "❄️ Winter",
    "summer": "🏖 Summer",
    "royal": "🎗 Royal",
    "luxury": "💸 Luxury Edition",
    "echhi": "🍃 echhi",
    "rainy": "🌧️ Rainy Edition",
    "festival": "🎍 Festival"
}

rarity_map2 = rarity_map


# -------------------------------
# FETCH USER CHARACTERS
# -------------------------------

async def fetch_user_characters(user_id):
    user = await user_collection.find_one({"id": user_id})
    if not user or "characters" not in user:
        return None, "You have not guessed any characters yet."

    characters = [c for c in user["characters"] if "id" in c]

    if not characters:
        return None, "No valid characters found in your collection."

    return characters, None


# -------------------------------
# /HAREM HANDLER
# -------------------------------

@app.on_message(filters.command(["harem", "collection"]))
async def harem_handler(client, message):
    user_id = message.from_user.id
    user = await user_collection.find_one({"id": user_id})
    filter_rarity = user.get("filter_rarity", None) if user else None

    page = 0

    sent = await display_harem(
        client, message, user_id, page, filter_rarity,
        is_initial=True
    )

    await asyncio.sleep(180)
    if sent:
        try:
            await sent.delete()
        except:
            pass


# -------------------------------
# MAIN DISPLAY FUNCTION
# -------------------------------

async def display_harem(client, message, user_id, page, filter_rarity, is_initial=False, callback_query=None):
    try:
        characters, error = await fetch_user_characters(user_id)
        if error:
            return await message.reply_text(error)

        characters = sorted(characters, key=lambda x: (x.get("anime", ""), x.get("id", "")))

        # Apply rarity filter
        if filter_rarity:
            filtered = [c for c in characters if c.get("rarity") == filter_rarity]
            if not filtered:
                keyboard = [
                    [InlineKeyboardButton("Remove Filter", callback_data=f"remove_filter:{user_id}")]
                ]
                return await message.reply_text(
                    f"No characters found with rarity: <b>{filter_rarity}</b>",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=enums.ParseMode.HTML
                )
            characters = filtered

        # Unique characters
        character_counts = {k: len(list(v)) for k, v in groupby(characters, key=lambda x: x["id"])}
        unique_characters = list({c["id"]: c for c in characters}.values())
        total_pages = max(1, math.ceil(len(unique_characters) / 15))

        if page >= total_pages:
            page = 0

        # Message
        harem_msg = f"<b>{escape(message.from_user.first_name)}'s Harem - Page {page + 1}/{total_pages}</b>\n"
        if filter_rarity:
            harem_msg += f"<b>Filtered by:</b> {filter_rarity}\n"

        current_chars = unique_characters[page * 15:(page + 1) * 15]
        grouped = {k: list(v) for k, v in groupby(current_chars, key=lambda x: x["anime"])}

        for anime, chars in grouped.items():
            total_in_anime = await collection.count_documents({"anime": anime})
            harem_msg += f"\n<b>{anime} {len(chars)}/{total_in_anime}</b>\n"
            for character in chars:
                rarity_emoji = rarity_map2.get(character.get("rarity"), "")
                count = character_counts[character["id"]]
                harem_msg += f"◈⌠{rarity_emoji}⌡ {character['id']} {character['name']} ×{count}\n"

        # Keyboard
        keyboard = [
            [
                InlineKeyboardButton("Collection", switch_inline_query_current_chat=f"collection.{user_id}"),
                InlineKeyboardButton("Animation 🎥", switch_inline_query_current_chat=f"collection.{user_id}.AMV"),
            ]
        ]

        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"harem:{page - 1}:{user_id}:{filter_rarity or 'None'}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f"harem:{page + 1}:{user_id}:{filter_rarity or 'None'}"))

        if nav_row:
            keyboard.append(nav_row)

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Preview image
        user = await user_collection.find_one({"id": user_id})
        fav = None
        if user and "favorites" in user and user["favorites"]:
            fav_id = user["favorites"][0]
            fav = next((c for c in characters if c["id"] == fav_id), None)

        image_character = fav or random.choice(characters)

        # Initial reply
        if is_initial:
            if "vid_url" in image_character:
                return await message.reply_video(
                    video=image_character["vid_url"],
                    caption=harem_msg,
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )

            elif "img_url" in image_character:
                return await message.reply_photo(
                    photo=image_character["img_url"],
                    caption=harem_msg,
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )

            else:
                return await message.reply_text(
                    harem_msg,
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )

        # Callback update
        if "img_url" in image_character:
            await callback_query.message.edit_media(
                InputMediaPhoto(image_character["img_url"], caption=harem_msg),
                reply_markup=reply_markup
            )
            return callback_query.message

        else:
            await callback_query.message.edit_text(
                harem_msg,
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            return callback_query.message

    except Exception as e:
        print("Error:", e)
        return await message.reply_text("An error occurred. Please try again later.")


# -------------------------------
# REMOVE FILTER
# -------------------------------

@app.on_callback_query(filters.regex(r"^remove_filter"))
async def remove_filter_callback(client, cq):
    try:
        _, user_id = cq.data.split(":")
        user_id = int(user_id)

        if cq.from_user.id != user_id:
            return await cq.answer("It's not your Harem!", show_alert=True)

        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"filter_rarity": None}},
            upsert=True
        )

        await cq.message.delete()
        await cq.answer("Filter removed!", show_alert=True)

    except Exception as e:
        print("Error remove filter:", e)


# -------------------------------
# NAVIGATION CALLBACK
# -------------------------------

@app.on_callback_query(filters.regex(r"^harem"))
async def harem_callback(client, cq):
    try:
        _, page, user_id, filter_rarity = cq.data.split(":")
        page = int(page)
        user_id = int(user_id)

        filter_rarity = None if filter_rarity == "None" else filter_rarity

        if cq.from_user.id != user_id:
            return await cq.answer("It's not your Harem!", show_alert=True)

        await display_harem(client, cq.message, user_id, page, filter_rarity, is_initial=False, callback_query=cq)

    except Exception as e:
        print("Error callback:", e)


# -------------------------------
# /HMODE COMMAND
# -------------------------------

@app.on_message(filters.command("hmode"))
async def hmode_handler(client, message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)

    # Case: /hmode rarity
    if len(args) > 1:
        rarity_input = args[1].strip().lower()

        if rarity_input in rarity_map:
            rarity_value = rarity_map[rarity_input]

            await user_collection.update_one(
                {"id": user_id},
                {"$set": {"filter_rarity": rarity_value}},
                upsert=True
            )

            c = await message.reply_text(
                f"Filter set to <b>{rarity_value}</b>",
                parse_mode=enums.ParseMode.HTML
            )
            await asyncio.sleep(3)
            await c.delete()
            return

        elif rarity_input in ["all", "none"]:
            await user_collection.update_one(
                {"id": user_id},
                {"$set": {"filter_rarity": None}},
                upsert=True
            )

            c = await message.reply_text("Filter cleared.")
            await asyncio.sleep(3)
            await c.delete()
            return

        else:
            available = ", ".join(v for v in rarity_map.values())
            return await message.reply_text(
                f"❌ Invalid rarity!\nAvailable: {available}",
                parse_mode=enums.ParseMode.HTML
            )

    # No args → show inline buttons
    keyboard, row = [], []
    for i, (key, value) in enumerate(rarity_map.items(), 1):
        row.append(InlineKeyboardButton(value, callback_data=f"set_rarity:{user_id}:{key}"))
        if i % 2 == 0:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("All", callback_data=f"set_rarity:{user_id}:None")])

    await message.reply_text("Select rarity:", reply_markup=InlineKeyboardMarkup(keyboard))


# -------------------------------
# RARITY BUTTON CALLBACK
# -------------------------------

@app.on_callback_query(filters.regex(r"^set_rarity:"))
async def set_rarity_callback(client, cq):
    try:
        await cq.answer()

        _, owner, rarity_key = cq.data.split(":")
        owner = int(owner)

        if cq.from_user.id != owner:
            return await cq.answer("Not your menu!", show_alert=True)

        rarity_value = None if rarity_key == "None" else rarity_map.get(rarity_key)

        await user_collection.update_one(
            {"id": owner},
            {"$set": {"filter_rarity": rarity_value}},
            upsert=True
        )

        txt = f"Filter set to <b>{rarity_value}</b>" if rarity_value else "Filter cleared."

        await cq.message.edit_text(txt, parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        print("Error rarity callback:", e)
