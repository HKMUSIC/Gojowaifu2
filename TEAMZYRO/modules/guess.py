from TEAMZYRO import (
    app,
    user_collection,
    top_global_groups_collection,
    last_characters,
    first_correct_guesses,
    user_guess_progress,
    check_cooldown,
    get_remaining_cooldown,
    react_to_message
)

from html import escape
import asyncio
import time
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message


# -------------------------------
# GUESS COMMAND
# -------------------------------

@app.on_message(filters.command(["guess", "protecc", "collect", "grab", "hunt"]))
async def guess(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    today = datetime.utcnow().date()

    # -----------------------------------
    # CHECK COOLDOWN
    # -----------------------------------
    try:
        if await check_cooldown(user_id):
            remaining_time = await get_remaining_cooldown(user_id)
            return await message.reply_text(
                f"⏳ You must wait {remaining_time} seconds before guessing again."
            )
    except:
        pass  # cooldown silently ignored if module failed

    # -----------------------------------
    # CHARACTER NOT AVAILABLE
    # -----------------------------------
    if chat_id not in last_characters or "name" not in last_characters[chat_id]:
        return await message.reply_text("❌ No active character to guess.")

    character = last_characters[chat_id]

    # -----------------------------------
    # ALREADY GUESSED
    # -----------------------------------
    if chat_id in first_correct_guesses:
        return await message.reply_text("❌ Someone already guessed the character!")

    # -----------------------------------
    # CHARACTER RAN AWAY
    # -----------------------------------
    if character.get("ranaway", False):
        return await message.reply_text("❌ The character already ran away!")

    # -----------------------------------
    # USER'S GUESS
    # -----------------------------------
    guess_text = " ".join(message.command[1:]).lower() if len(message.command) > 1 else ""

    if not guess_text:
        return await message.reply_text("❌ Please type the character name after /guess.")

    # security check
    if "()" in guess_text or "&" in guess_text:
        return await message.reply_text("⚠️ Invalid characters used in guess.")

    name_parts = character["name"].lower().split()

    # -----------------------------------
    # CORRECT GUESS
    # -----------------------------------
    if sorted(name_parts) == sorted(guess_text.split()) or any(
        part == guess_text for part in name_parts
    ):
        first_correct_guesses[chat_id] = user_id

        # SAFE TIMER CANCEL (prevents task-destroyed errors)
        for task in list(asyncio.all_tasks()):
            if task.get_name() == f"expire_session_{chat_id}" and not task.done():
                task.cancel()

        timestamp = character.get("timestamp", time.time())
        time_taken = max(0, int(time.time() - timestamp))

        # -----------------------------------
        # Update user's daily guess count
        # -----------------------------------
        if user_id not in user_guess_progress or user_guess_progress[user_id]["date"] != today:
            user_guess_progress[user_id] = {"date": today, "count": 0}

        user_guess_progress[user_id]["count"] += 1

        # -----------------------------------
        # Add character to user
        # -----------------------------------
        user = await user_collection.find_one({"id": user_id})

        if user:
            await user_collection.update_one(
                {"id": user_id},
                {"$push": {"characters": character}}
            )
        else:
            await user_collection.insert_one({
                "id": user_id,
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "characters": [character],
                "balance": 0
            })

        # unlock balance
        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"lockbalance": False}}
        )

        # -----------------------------------
        # Group ranking update
        # -----------------------------------
        if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await top_global_groups_collection.update_one(
                {"chat_id": chat_id},
                {"$set": {"group_name": message.chat.title}},
                upsert=True
            )
            await top_global_groups_collection.update_one(
                {"chat_id": chat_id}, {"$inc": {"count": 1}}
            )

        # run reaction system
        try:
            await react_to_message(chat_id, message.id)
        except:
            pass

        # -----------------------------------
        # Add coins
        # -----------------------------------
        user = await user_collection.find_one({"id": user_id})
        bal = user.get("balance", 0) + 40

        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"balance": bal}}
        )

        # -----------------------------------
        # Send success message
        # -----------------------------------

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]
        ])

        return await message.reply_text(
            f"🎉 <b>{escape(message.from_user.first_name)}</b> guessed correctly!\n\n"
            f"📛 <b>Name:</b> {character['name']}\n"
            f"🌈 <b>Anime:</b> {character['anime']}\n"
            f"✨ <b>Rarity:</b> {character['rarity']}\n"
            f"⏱️ <b>Time Taken:</b> {time_taken} sec\n\n"
            f"💰 Earned: <b>40 coins</b>\n"
            f"💼 New Balance: <code>{bal}</code>",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=kb
        )

    # -----------------------------------
    # WRONG GUESS
    # -----------------------------------
    msg_id = character.get("message_id")

    if msg_id and str(chat_id).startswith("-100"):
        # fix for t.me/c link
        fixed_id = str(chat_id)[4:]
        url = f"https://t.me/c/{fixed_id}/{msg_id}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("See Media Again", url=url)]])
    else:
        kb = None

    return await message.reply_text(
        "❌ Wrong guess! Try again!",
        reply_markup=kb
        )
