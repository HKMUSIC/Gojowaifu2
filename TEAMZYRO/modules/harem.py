from TEAMZYRO import app, user_collection, collection
from pyrogram import filters, enums
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
# Helper: fetch & validate user's characters
# -------------------------------
async def fetch_user_characters(user_id):
    doc = await user_collection.find_one({"id": user_id})
    if not doc or "characters" not in doc:
        return None, "You have not guessed any characters yet."

    valid = []
    for c in doc.get("characters", []):
        if not isinstance(c, dict):
            continue
        # require id and name at minimum; if missing try to repair from main collection
        cid = c.get("id")
        if not cid or "name" not in c:
            if cid:
                main = await collection.find_one({"id": cid})
                if main:
                    valid.append(main)
            continue
        valid.append(c)

    if not valid:
        return None, "No valid characters found in your collection."
    return valid, None


# -------------------------------
# /harem handler (entry)
# -------------------------------
@app.on_message(filters.command(["harem", "collection"]))
async def harem_handler(client: app.__class__, message: Message):
    user_id = message.from_user.id
    user_doc = await user_collection.find_one({"id": user_id})
    filter_rarity = user_doc.get("filter_rarity") if user_doc else None
    page = 0

    # display_harem will send or reply safely and return the message when it sent one
    await display_harem(client, message, user_id, page, filter_rarity, is_initial=True)


# -------------------------------
# Main display function (robust)
# -------------------------------
async def display_harem(client, message: Message | None, user_id: int, page: int, filter_rarity, is_initial=False, callback_query: CallbackQuery = None):
    """
    Sends or edits a harem message safely. If callback_query is provided but its .message is None (inline), we
    fall back to callback answer or DM the user.
    """
    try:
        characters, error = await fetch_user_characters(user_id)
        if error:
            # respond via callback if present, otherwise reply in chat (if message exists)
            if callback_query:
                try:
                    await callback_query.answer(error, show_alert=True)
                except Exception:
                    # attempt DM fallback
                    try:
                        await client.send_message(callback_query.from_user.id, error)
                    except Exception:
                        pass
                return None
            if message:
                return await message.reply_text(error)
            return None

        # sort & (optionally) filter
        characters = sorted(characters, key=lambda x: (x.get("anime", "") or "", str(x.get("id", ""))))
        if filter_rarity:
            filtered = [c for c in characters if c.get("rarity") == filter_rarity]
            if not filtered:
                kb = [[InlineKeyboardButton("Remove Filter", callback_data=f"remove_filter:{user_id}")]]
                text = f"No characters found with rarity: <b>{escape(str(filter_rarity))}</b>"
                if callback_query and callback_query.message:
                    return await callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=enums.ParseMode.HTML)
                if callback_query:
                    try:
                        await callback_query.answer(text, show_alert=True)
                    except Exception:
                        pass
                    return None
                if message:
                    return await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=enums.ParseMode.HTML)
                return None
            characters = filtered

        # compute counts & pagination
        character_counts = {}
        for k, g in groupby(characters, key=lambda x: x["id"]):
            group_list = list(g)
            character_counts[k] = len(group_list)

        # keep last occurrence for best data
        uniq = {}
        for c in characters:
            uniq[c["id"]] = c
        unique_characters = list(uniq.values())

        total_pages = max(1, math.ceil(len(unique_characters) / 15))
        if page < 0 or page >= total_pages:
            page = 0

        # message header - prefer callback_query.from_user when message might be None
        display_name = None
        if callback_query and getattr(callback_query, "from_user", None):
            display_name = callback_query.from_user.first_name or "User"
        elif message and getattr(message, "from_user", None):
            display_name = message.from_user.first_name or "User"
        else:
            display_name = "User"

        harem_msg = f"<b>{escape(display_name)}'s Harem - Page {page+1}/{total_pages}</b>\n"
        if filter_rarity:
            harem_msg += f"<b>Filtered by:</b> {escape(str(filter_rarity))}\n"

        current_chars = unique_characters[page * 15:(page + 1) * 15]
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

        # keyboard
        keyboard = [
            [
                InlineKeyboardButton("Collection", switch_inline_query_current_chat=f"collection.{user_id}"),
                InlineKeyboardButton("Animation 🎥", switch_inline_query_current_chat=f"collection.{user_id}.AMV"),
            ]
        ]
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"harem:{page-1}:{user_id}:{filter_rarity or 'None'}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"harem:{page+1}:{user_id}:{filter_rarity or 'None'}"))
        if nav:
            keyboard.append(nav)
        reply_markup = InlineKeyboardMarkup(keyboard)

        # choose preview media safely
        user_doc = await user_collection.find_one({"id": user_id})
        fav = None
        if user_doc and isinstance(user_doc.get("favorites"), (list, tuple)) and user_doc.get("favorites"):
            fav_id = user_doc["favorites"][0]
            fav = next((c for c in characters if c.get("id") == fav_id), None)

        image_character = fav or next((c for c in characters if c.get("vid_url")), None) or next((c for c in characters if c.get("img_url")), None) or (random.choice(characters) if characters else None)

        # if nothing to show, fallback to text-only
        if not image_character:
            if callback_query and callback_query.message:
                return await callback_query.message.reply_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            if message:
                return await message.reply_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            if callback_query:
                try:
                    await callback_query.answer("No media to display. Check your DM.", show_alert=True)
                    await client.send_message(callback_query.from_user.id, harem_msg, parse_mode=enums.ParseMode.HTML)
                except Exception:
                    pass
                return None
            return None

        # initial send
        if is_initial:
            if image_character.get("vid_url"):
                if message:
                    return await message.reply_video(video=image_character["vid_url"], caption=harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                if callback_query:
                    return await client.send_video(callback_query.from_user.id, video=image_character["vid_url"], caption=harem_msg, parse_mode=enums.ParseMode.HTML)
            elif image_character.get("img_url"):
                if message:
                    return await message.reply_photo(photo=image_character["img_url"], caption=harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                if callback_query:
                    return await client.send_photo(callback_query.from_user.id, photo=image_character["img_url"], caption=harem_msg, parse_mode=enums.ParseMode.HTML)
            else:
                if message:
                    return await message.reply_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                if callback_query:
                    return await client.send_message(callback_query.from_user.id, harem_msg, parse_mode=enums.ParseMode.HTML)

        # callback edits
        if not callback_query:
            return None

        if not callback_query.message:
            try:
                await callback_query.answer("Cannot update inline message here. Check your DM.", show_alert=True)
                await client.send_message(callback_query.from_user.id, harem_msg, parse_mode=enums.ParseMode.HTML)
            except Exception:
                try:
                    await callback_query.answer("Cannot update here.", show_alert=True)
                except Exception:
                    pass
            return None

        # edit with media/text safely
        if image_character.get("vid_url"):
            try:
                await callback_query.message.edit_media(InputMediaVideo(image_character["vid_url"], caption=harem_msg), reply_markup=reply_markup)
                return callback_query.message
            except Exception:
                await callback_query.message.edit_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                return callback_query.message
        elif image_character.get("img_url"):
            try:
                await callback_query.message.edit_media(InputMediaPhoto(image_character["img_url"], caption=harem_msg), reply_markup=reply_markup)
                return callback_query.message
            except Exception:
                await callback_query.message.edit_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                return callback_query.message
        else:
            await callback_query.message.edit_text(harem_msg, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            return callback_query.message

    except Exception as e:
        # server-side log for debugging
        uid = None
        try:
            if callback_query and getattr(callback_query, "from_user", None):
                uid = callback_query.from_user.id
            elif message and getattr(message, "from_user", None):
                uid = message.from_user.id
        except Exception:
            pass
        print("Harem error for user", uid, ":", repr(e))
        # reply safely
        if callback_query:
            try:
                await callback_query.answer("An error occurred. Please try again later.", show_alert=True)
            except Exception:
                pass
            return None
        if message:
            try:
                return await message.reply_text("An error occurred. Please try again later.")
            except Exception:
                return None
        return None


# -------------------------------
# REMOVE FILTER CALLBACK
# -------------------------------
@app.on_callback_query(filters.regex(r"^remove_filter"))
async def remove_filter_callback(client, cq: CallbackQuery):
    try:
        parts = cq.data.split(":")
        if len(parts) != 2:
            return await cq.answer("Invalid data.", show_alert=True)
        _, uid = parts
        uid = int(uid)

        if cq.from_user.id != uid:
            return await cq.answer("It's not your Harem!", show_alert=True)

        await user_collection.update_one({"id": uid}, {"$set": {"filter_rarity": None}}, upsert=True)

        if cq.message:
            try:
                await cq.message.delete()
            except Exception:
                pass

        await cq.answer("Filter removed!", show_alert=True)
    except Exception as e:
        print("Error remove_filter:", repr(e))
        try:
            await cq.answer("An error occurred.", show_alert=True)
        except Exception:
            pass


# -------------------------------
# NAVIGATION CALLBACK
# -------------------------------
@app.on_callback_query(filters.regex(r"^harem"))
async def harem_callback(client, cq: CallbackQuery):
    try:
        parts = cq.data.split(":")
        if len(parts) != 4:
            return await cq.answer("Invalid data.", show_alert=True)
        _, page_s, uid_s, filter_r = parts
        try:
            page = int(page_s)
            uid = int(uid_s)
        except ValueError:
            return await cq.answer("Invalid page/user id.", show_alert=True)

        filter_rarity = None if filter_r == "None" else filter_r

        if cq.from_user.id != uid:
            return await cq.answer("It's not your Harem!", show_alert=True)

        await display_harem(client, cq.message, uid, page, filter_rarity, is_initial=False, callback_query=cq)

    except Exception as e:
        print("Error harem callback:", repr(e))
        try:
            await cq.answer("An error occurred.", show_alert=True)
        except Exception:
            pass


# -------------------------------
# /hmode command (sets filter)
# -------------------------------
@app.on_message(filters.command("hmode"))
async def hmode_handler(client, message: Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        rarity_input = args[1].strip().lower()

        if rarity_input in rarity_map:
            rarity_value = rarity_map[rarity_input]
            await user_collection.update_one({"id": user_id}, {"$set": {"filter_rarity": rarity_value}}, upsert=True)
            return await message.reply_text(f"✅ Filter set to: <b>{escape(rarity_value)}</b>", parse_mode=enums.ParseMode.HTML)

        if rarity_input in ("all", "none"):
            await user_collection.update_one({"id": user_id}, {"$set": {"filter_rarity": None}}, upsert=True)
            return await message.reply_text("✅ Filter cleared. Showing all rarities.")

        available = ", ".join(v for v in rarity_map.values())
        return await message.reply_text(f"❌ Invalid rarity!\nAvailable: {available}", parse_mode=enums.ParseMode.HTML)

    # no args → show inline buttons
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
# SET RARITY CALLBACK
# -------------------------------
@app.on_callback_query(filters.regex(r"^set_rarity:"))
async def set_rarity_callback(client, cq: CallbackQuery):
    try:
        await cq.answer()
        parts = cq.data.split(":")
        if len(parts) != 3:
            return await cq.answer("Invalid data.", show_alert=True)
        _, owner_s, rarity_key = parts
        owner = int(owner_s)
        if cq.from_user.id != owner:
            return await cq.answer("Not your menu!", show_alert=True)

        rarity_value = None if rarity_key == "None" else rarity_map.get(rarity_key)
        await user_collection.update_one({"id": owner}, {"$set": {"filter_rarity": rarity_value}}, upsert=True)

        txt = f"✅ Filter set to: <b>{escape(str(rarity_value))}</b>" if rarity_value else "✅ Filter cleared."
        if cq.message:
            try:
                await cq.message.edit_text(txt, parse_mode=enums.ParseMode.HTML)
            except Exception:
                pass
        await cq.answer("Saved.", show_alert=False)
    except Exception as e:
        print("Error set_rarity:", repr(e))
        try:
            await cq.answer("Error setting rarity.", show_alert=True)
        except Exception:
            pass
