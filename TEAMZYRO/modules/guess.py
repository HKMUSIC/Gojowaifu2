from TEAMZYRO import *
from TEAMZYRO import application
from html import escape
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram import enums
from datetime import datetime

@app.on_message(filters.command(["guess", "protecc", "collect", "grab", "hunt"]))
async def guess(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    today = datetime.utcnow().date()

    # COOLDOWN CHECK
    if await check_cooldown(user_id):
        remaining_time = await get_remaining_cooldown(user_id)
        return await message.reply_text(
            f"⚠️ You are still in cooldown. Please wait {remaining_time} seconds."
        )

    # CHECK IF CHARACTER EXISTS
    if chat_id not in last_characters or 'name' not in last_characters[chat_id]:
        return await message.reply_text("❌ Character Guess not available")

    # ALREADY GUESSED
    if chat_id in first_correct_guesses:
        return await message.reply_text("❌ Character already guessed!")

    # RAN AWAY
    if last_characters[chat_id].get('ranaway', False):
        return await message.reply_text("❌ THE CHARACTER HAS ALREADY RUN AWAY!")

    # USER GUESS
    guess = ' '.join(message.command[1:]).lower() if len(message.command) > 1 else ''

    if "()" in guess or "&" in guess.lower():
        return await message.reply_text("❌ You can't use those characters in guess!")

    name_parts = last_characters[chat_id]['name'].lower().split()

    # -------------------------------
    # CORRECT GUESS
    # -------------------------------
    if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):

        first_correct_guesses[chat_id] = user_id

        # Cancel runaway timer
        for task in asyncio.all_tasks():
            if task.get_name() == f"expire_session_{chat_id}":
                task.cancel()
                break

        timestamp = last_characters[chat_id].get('timestamp')
        time_taken = time.time() - timestamp if timestamp else 0
        time_taken_str = f"{int(time_taken)} seconds"

        # Daily guess count
        if user_id not in user_guess_progress or user_guess_progress[user_id]["date"] != today:
            user_guess_progress[user_id] = {"date": today, "count": 0}
        user_guess_progress[user_id]["count"] += 1

        # Fetch or create user
        user = await user_collection.find_one({'id': user_id})
        if user:
            update_fields = {}
            if message.from_user.username != user.get('username'):
                update_fields['username'] = message.from_user.username
            if message.from_user.first_name != user.get('first_name'):
                update_fields['first_name'] = message.from_user.first_name
            
            if update_fields:
                await user_collection.update_one({'id': user_id}, {'$set': update_fields})

            await user_collection.update_one(
                {'id': user_id},
                {'$push': {'characters': last_characters[chat_id]}}
            )
        else:
            await user_collection.insert_one({
                'id': user_id,
                'username': message.from_user.username,
                'first_name': message.from_user.first_name,
                'characters': [last_characters[chat_id]],
            })

        # AUTO-UNLOCK BALANCE
        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"lockbalance": False}}
        )

        # Update group count
        if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            group_name = message.chat.title or f"Group_{chat_id}"
            await top_global_groups_collection.update_one(
                {'chat_id': chat_id},
                {'$set': {'group_name': group_name}, '$inc': {'count': 1}},
                upsert=True
            )

        await react_to_message(chat_id, message.id)

        # Add coins
        user = await user_collection.find_one({'id': user_id})
        current_balance = user.get('balance', 0)
        new_balance = current_balance + 40

        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'balance': new_balance}}
        )

        await message.reply_text(
            f"🎉 You earned **40 coins!**\n💰 New Balance: `{new_balance}` coins"
        )

        # Send Character Info
        keyboard = [
            [InlineKeyboardButton("See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]
        ]

        return await message.reply_text(
            f'🌟 <b><a href="tg://user?id={user_id}">{escape(message.from_user.first_name)}</a></b> guessed the character! 🎊\n\n'
            f'📛 <b>Name:</b> {last_characters[chat_id]["name"]}\n'
            f'🌈 <b>Anime:</b> {last_characters[chat_id]["anime"]}\n'
            f'✨ <b>Rarity:</b> {last_characters[chat_id]["rarity"]}\n'
            f'⏱️ <b>Time Taken:</b> {time_taken_str}\n\n'
            f'This character has been added to your Harem.',
            parse_mode=enums.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # -------------------------------
    # WRONG GUESS
    # -------------------------------
    else:
        msg_id = last_characters[chat_id].get('message_id')
        if msg_id:
            keyboard = [
                [InlineKeyboardButton("See Media Again", url=f"https://t.me/c/{str(chat_id)[4:]}/{msg_id}")]
            ]
            return await message.reply_text(
                "❌ Wrong guess! Try again! 🕵️‍♂️",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        return await message.reply_text("❌ Wrong guess! Try again! 🕵️‍♂️")
