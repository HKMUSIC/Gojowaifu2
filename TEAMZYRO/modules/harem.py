from TEAMZYRO import *
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
    CallbackQuery,
    Message,
)
from itertools import groupby
import math
import random
import asyncio
from html import escape
from pyrogram.errors import ChatAdminRequired, UserNotParticipant, ChatWriteForbidden

# -------------------------------
# USE SAME RARITY MAP
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
rarity_map2 = rarity_map  # same alias for backwards-compatibility


# -------------------------------
# Helper: fetch & validate user's characters
# -------------------------------
async def fetch_user_characters(user_id):
    user = await user_collection.find_one({"id": user_id})
    if not user or "characters" not in user:
        return None, "You have not guessed any characters yet."

    # Filter out any corrupt/missing entries early
    valid_chars = []
    for c in user.get("characters", []):
        # require at least id and name; image/video optional but we'll try to prefer those later
        if not isinstance(c, dict):
            continue
        if "id" not in c or "name" not in c:
            # try to repair from main collection if possible
            main = await collection.find_one({"id": c.get("id")}) if c.get("id") else None
            if main:
                valid_chars.append(main)
            else:
                # skip broken entry
                continue
        else:
            valid_chars.append(c)

    if not valid_chars:
        return None, "No valid characters found in your collection."

    return valid_chars, None


# -------------------------------
# /harem handler (entry)
# -------------------------------
@app.on_message(filters.command(["harem", "collection"]))
async def harem_handler(client: Client, message: Message):
    user_id = message.from_user.id
    user = await user_collection.find_one({"id": user_id})
    filter_rarity = user.get("filter_rarity", None) if user else None
    page = 0

    # display_harem returns the sent message object (or None)
    sent = await display_harem(client, message, user_id, page, filter_rarity, is_initial=True)

    # Auto-delete after 3 minutes if message was sent
    await asyncio.sleep(180)
    if sent:
        try:
            await sent.delete()
        except Exception:
            # ignore delete failures silently
            pass


# -------------------------------
# Display function (returns message when sending)
# -------------------------------
async def display_harem(client, message: Message, user_id: int, page: int, filter_rarity, is_initial=False, callback_query: CallbackQuery = None):
    """
    Returns: the sent Message object (when is_initial True), or callback_query.message (when is_initial False)
    """
    try:
        characters, error = await fetch_user_characters(user_id)
        if error:
            # If callback context (button), reply via answer or send a message fallback
            if callback_query and callback_query.message:
                await callback_query.message.reply_text(error)
                return callback_query.message
            return await message.reply_text(error)

        # Sort characters by anime and ID (stable)
        characters = sorted(characters, key=lambda x: (x.get("anime", "") or "", str(x.get("id", ""))))

        # Apply rarity filter if present
        if filter_rarity:
            filtered = [c for c in characters if c.get("rarity") == filter_rarity]
            if not filtered:
                keyboard = [[InlineKeyboardButton("Remove Filter", callback_data=f"remove_filter:{user_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                if callback_query and callback_query.message:
                    await callback_query.message.reply_text(
                        f"No characters found with rarity: <b>{escape(str(filter_rarity))}</b>",
                        reply_markup=reply_markup,
                        parse_mode=enums.ParseMode.HTML
                    )
                    return callback_query.message
                return await message.reply_text(
                    f"No characters found with rarity: <b>{escape(str(filter_rarity))}</b>",
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
            characters = filtered

        # Remove duplicates for listing purpose but keep counts
        # groupby requires sorted by key, so we already sorted by id indirectly, but ensure unique preserving last occurrence
        character_counts = {}
        for k, group in groupby(characters, key=lambda x: x["id"]):
            group_list = list(group)
            character_counts[k] = len(group_list)

        # unique_characters: keep last occurrence so it has most complete fields
        unique_map = {}
        for c in characters:
            unique_map[c["id"]] = c
        unique_characters = list(unique_map.values())

        total_pages = max(1, math.ceil(len(unique_characters) / 15))
        if page < 0 or page >= total_pages:
            page = 0

        # Build message text
        harem_msg = f"<b>{escape(message.from_user.first_name or 'User')}'s Harem - Page {page+1}/{total_pages}</b>\n"
        if filter_rarity:
            harem_msg += f"<b>Filtered by:</b> {escape(str(filter_rarity))}\n"

        current_chars = unique_characters[page * 15:(page + 1) * 15]
        # group by anime for display
        grouped = {}
        for c in current_chars:
            anime = c.get("anime") or "Unknown"
            grouped.setdefault(anime, []).append(c)

        for anime, chars in grouped.items():
            total_in_anime = await collection.count_documents({"anime": anime}) if anime != "Unknown" else 0
            harem_msg += f"\n<b>{escape(str(anime))} {len(chars)}/{total_in_anime}</b>\n"
            for character in chars:
                rarity_emoji = rarity_map2.get(character.get("rarity"), character.get("rarity", ""))
                count = character_counts.get(character["id"], 1)
                cname = escape(str(character.get("name", "Unknown")))
                cid = escape(str(character.get("id")))
                harem_msg += f"◈⌠{rarity_emoji}⌡ {cid} {cname} ×{count}\n"

        # Build keyboard
        keyboard = [
            [
                InlineKeyboardButton("Collection", switch_inline_query_current_chat=f"collection.{user_id}"),
                InlineKeyboardButton("Animation 🎥", switch_inline_query_current_chat=f"collection.{user_id}.AMV"),
            ]
        ]
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"harem:{page-1}:{user_id}:{filter_rarity or 'None'}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f"harem:{page+1}:{user_id}:{filter_rarity or 'None'}"))
        if nav_row:
            keyboard.append(nav_row)
        reply_markup = InlineKeyboardMarkup(keyboard)

        # ---------- choose preview media safely ----------
        # try favorites first (but only if that fav exists in user's characters list)
        user = await user_collection.find_one({"id": user_id})
        fav = None
        if user and isinstance(user.get("favorites"), (list, tuple)) and user.get("favorites"):
            fav_id = user["favorites"][0]
            fav = next((c for c in characters if c.get("id") == fav_id), None)

        # prefer fav, else find first character that has vid/img, else any character
        image_character = None
        if fav:
            image_character = fav
        else:
            # find any char with vid_url first
            image_character = next((c for c in characters if c.get("vid_url")), None)
            if not image_character:
                image_character = next((c for c in characters if c.get("img_url")), None)
            if not image_character and characters:
                image_character = random.choice(characters)

        # Still nothing (shouldn't happen after validation), fallback to text-only
        if not image_character:
            if is_initial:
                return await message.reply_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            else:
                if not callback_query or not callback_query.message:
                    # cannot edit inline message
                    return await message.reply_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                await callback_query.message.edit_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                return callback_query.message

        # ---------- SEND or EDIT ----------

        # initial send (reply with proper media type)
        if is_initial:
            if image_character.get("vid_url"):
                return await message.reply_video(
                    video=image_character["vid_url"],
                    caption=harem_msg,
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
            elif image_character.get("img_url"):
                return await message.reply_photo(
                    photo=image_character["img_url"],
                    caption=harem_msg,
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
            else:
                return await message.reply_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)

        # callback edit: ensure callback_query.message exists (not inline message)
        if not callback_query or not callback_query.message:
            # can't edit because this might be an inline message; just answer
            if callback_query:
                await callback_query.answer("Cannot update inline message here.", show_alert=True)
            return None

        # edit media or text depending on available media
        if image_character.get("vid_url"):
            try:
                await callback_query.message.edit_media(
                    InputMediaVideo(image_character["vid_url"], caption=harem_msg),
                    reply_markup=reply_markup
                )
                return callback_query.message
            except Exception:
                # fallback to edit_text if edit_media fails
                await callback_query.message.edit_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                return callback_query.message

        elif image_character.get("img_url"):
            try:
                await callback_query.message.edit_media(
                    InputMediaPhoto(image_character["img_url"], caption=harem_msg),
                    reply_markup=reply_markup
                )
                return callback_query.message
            except Exception:
                await callback_query.message.edit_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                return callback_query.message

        else:
            await callback_query.message.edit_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            return callback_query.message

    except Exception as e:
        # Log full error server-side for debugging (avoid spamming user with stack traces)
        print("Harem display error for user", getattr(message.from_user, "id", None), "error:", repr(e))
        try:
            return await message.reply_text("An error occurred. Please try again later.")
        except Exception:
            # If reply fails (e.g., called from callback where message is unavailable), no-op
            return None


# -------------------------------
# Remove filter callback
# -------------------------------
@app.on_callback_query(filters.regex(r"^remove_filter"))
async def remove_filter_callback(client, cq: CallbackQuery):
    try:
        parts = cq.data.split(":")
        if len(parts) != 2:
            return await cq.answer("Invalid data.", show_alert=True)
        _, user_id = parts
        user_id = int(user_id)

        if cq.from_user.id != user_id:
            return await cq.answer("It's not your Harem!", show_alert=True)

        await user_collection.update_one({"id": user_id}, {"$set": {"filter_rarity": None}}, upsert=True)

        # delete message only if available (not inline)
        if cq.message:
            try:
                await cq.message.delete()
            except Exception:
                pass

        await cq.answer("Filter removed!", show_alert=True)

    except Exception as e:
        print("Error remove_filter callback:", repr(e))
        try:
            await cq.answer("An error occurred.", show_alert=True)
        except Exception:
            pass


# -------------------------------
# Navigation callback
# -------------------------------
@app.on_callback_query(filters.regex(r"^harem"))
async def harem_callback(client, cq: CallbackQuery):
    try:
        parts = cq.data.split(":")
        if len(parts) != 4:
            return await cq.answer("Invalid data.", show_alert=True)
        _, page_s, user_id_s, filter_rarity_raw = parts
        try:
            page = int(page_s)
            user_id = int(user_id_s)
        except ValueError:
            return await cq.answer("Invalid page/user id.", show_alert=True)

        filter_rarity = None if filter_rarity_raw == "None" else filter_rarity_raw

        if cq.from_user.id != user_id:
            return await cq.answer("It's not your Harem!", show_alert=True)

        await display_harem(client, cq.message or Message, user_id, page, filter_rarity, is_initial=False, callback_query=cq)

    except Exception as e:
        print("Error callback:", repr(e))
        try:
            await cq.answer("An error occurred.", show_alert=True)
        except Exception:
            pass


# -------------------------------
# /hmode command
# -------------------------------
@app.on_message(filters.command("hmode"))
async def hmode_handler(client, message: Message):

    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)

    # case: user typed /hmode rarity
    if len(args) > 1:
        rarity_input = args[1].strip().lower()

        if rarity_input in rarity_map:
            rarity_value = rarity_map[rarity_input]

            await user_collection.update_one(
                {"id": user_id},
                {"$set": {"filter_rarity": rarity_value}},
                upsert=True
            )

            c = await message.reply_text(f"Filter set to <b>{escape(rarity_value)}</b>", parse_mode=enums.ParseMode.HTML)
            await asyncio.sleep(3)
            try:
                await c.delete()
            except Exception:
                pass
            return

        elif rarity_input in ["all", "none"]:
            await user_collection.update_one(
                {"id": user_id},
                {"$set": {"filter_rarity": None}},
                upsert=True
            )
            c = await message.reply_text("Filter cleared.")
            await asyncio.sleep(3)
            try:
                await c.delete()
            except Exception:
                pass
            return

        else:
            available = ", ".join(v for v in rarity_map.values())
            return await message.reply_text(
                f"❌ Invalid rarity!\nAvailable: {available}",
                parse_mode=enums.ParseMode.HTML
            )

    # no args → send inline buttons
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
# Rarity filter button callback
# -------------------------------
@app.on_callback_query(filters.regex(r"^set_rarity:"))
async def set_rarity_callback(client, cq: CallbackQuery):
    try:
        await cq.answer()

        parts = cq.data.split(":")
        if len(parts) != 3:
            return await cq.answer("Invalid data.", show_alert=True)
        _, owner, rarity_key = parts
        owner = int(owner)

        if cq.from_user.id != owner:
            return await cq.answer("Not your menu!", show_alert=True)

        rarity_value = None if rarity_key == "None" else rarity_map.get(rarity_key)

        await user_collection.update_one(
            {"id": owner},
            {"$set": {"filter_rarity": rarity_value}},
            upsert=True
        )

        txt = f"Filter set to <b>{escape(str(rarity_value))}</b>" if rarity_value else "Filter cleared."

        # edit message text if possible
        if cq.message:
            try:
                await cq.message.edit_text(txt, parse_mode=enums.ParseMode.HTML)
            except Exception:
                pass

        await cq.answer("🎉 Your rarity set successfully!", show_alert=False)

    except Exception as e:
        print("Error rarity callback:", repr(e))
        try:
            await cq.answer("❌ Error setting rarity filter", show_alert=True)
        except Exception:
            pass
