import asyncio
from random import choice, randint

import html
from random import randint, choice
from pyrogram import Client, filters
from pyrogram.types import Message

# database imports
from Database import user_collection, characters_col
from Utils.cooldown import check_cooldown, get_remaining_cooldown  # only if you use cooldown

# optional if you use cooldowns
# from Utils.cooldown import check_cooldown, get_remaining_cooldown

last_challenges = {}  # store current active challenges per chat

@app.on_message(filters.command("challenge_spawn"))
async def challenge_spawn(client: Client, message: Message):
    chat_id = message.chat.id

    # Fetch all waifus from DB (replace 'characters_col' with your waifu collection)
    all_chars = await characters_col.find().to_list(None)
    if not all_chars:
        await message.reply_text("❌ No waifus available in database.")
        return

    char = choice(all_chars)
    last_challenges[chat_id] = char  # store current waifu

    caption = (
        f"💫 A mysterious waifu has appeared! 💫\n"
        f"Type `/challenge {char['name']}` to fight her!"
    )

    await message.reply_photo(
        photo=char["image"],
        caption=caption,
        has_spoiler=True  # spoiler mode ON
  )

@app.on_message(filters.command("challenge"))
async def challenge(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if challenge waifu exists
    if chat_id not in last_challenges:
        await message.reply_text("❌ No waifu to challenge right now! Use /challenge_spawn first.")
        return

    waifu = last_challenges[chat_id]
    guess = ' '.join(message.command[1:]).strip().lower()

    if not guess:
        await message.reply_text("Usage: `/challenge <character name>`", quote=True)
        return

    # Compare guessed name
    if guess != waifu["name"].lower():
        await message.reply_text(f"❌ Wrong challenge name! Try again.")
        return

    # Remove the waifu after a valid challenge attempt
    del last_challenges[chat_id]

    # Random fight result
    result = choice(["win", "lose"])
    strength = choice(["strong", "weak"])

    char_name = waifu["name"]
    user_name = message.from_user.first_name

    if result == "win":
        reward = randint(200, 500)
        await user_collection.update_one(
            {"id": user_id},
            {"$inc": {"balance": reward}},
            upsert=True
        )

        await message.reply_text(
            f"⚔️ {user_name} challenged {char_name}!\n"
            f"The fight was amazing — {char_name} was **{strength}**, but you emerged victorious! 🏆\n\n"
            f"💰 You won {reward} coins!"
        )
    else:
        await message.reply_text(
            f"⚔️ {user_name} challenged {char_name}!\n"
            f"The fight was intense — {char_name} was **{strength}**, and you lost this time. 😢\n"
            f"Better luck next challenge!"
  )


if await check_cooldown(user_id):
    remaining_time = await get_remaining_cooldown(user_id)
    await message.reply_text(
        f"⚠️ You're in cooldown. Try again in {remaining_time} seconds."
    )
    return

@app.on_message(filters.command("rob"))
async def rob_command(client: Client, message: Message):
    try:
        # Must be a reply to a user's message
        if not message.reply_to_message or not message.reply_to_message.from_user:
            await message.reply_text("Usage: Reply to a user's message with /rob to rob them.")
            return

        robber_id = message.from_user.id
        robber_name = message.from_user.first_name or str(robber_id)

        target = message.reply_to_message.from_user
        target_id = target.id
        target_name = target.first_name or str(target_id)

        # Prevent robbing self or the bot
        if target_id == robber_id:
            await message.reply_text("You cannot rob yourself 😅")
            return

        try:
            bot_id = (await client.get_me()).id
            if target_id == bot_id or robber_id == bot_id:
                await message.reply_text("You cannot rob the bot.")
                return
        except Exception:
            pass  # ignore get_me errors

        # Ensure both users exist in DB (create minimal docs if missing)
        robber_doc = await user_collection.find_one({'id': robber_id})
        if not robber_doc:
            await user_collection.insert_one({
                'id': robber_id,
                'username': message.from_user.username,
                'first_name': message.from_user.first_name,
                'balance': 0
            })
            robber_doc = {'id': robber_id, 'balance': 0}

        target_doc = await user_collection.find_one({'id': target_id})
        if not target_doc:
            await user_collection.insert_one({
                'id': target_id,
                'username': target.username if hasattr(target, 'username') else None,
                'first_name': target.first_name if hasattr(target, 'first_name') else None,
                'balance': 0
            })
            target_doc = {'id': target_id, 'balance': 0}

        # Random amount between 50 and 90
        amount = randint(50, 90)
        current_robber_balance = robber_doc.get('balance', 0)

        if current_robber_balance < amount:
            await message.reply_text(
                f"❌ Insufficient balance. You need {amount} coins but you have {current_robber_balance}."
            )
            return

        # Perform transfer
        await user_collection.update_one({'id': robber_id}, {'$inc': {'balance': -amount}})
        await user_collection.update_one({'id': target_id}, {'$inc': {'balance': amount}})

        # Fetch updated balances
        updated_robber = await user_collection.find_one({'id': robber_id})
        updated_target = await user_collection.find_one({'id': target_id})
        updated_robber_balance = updated_robber.get('balance', 0)
        updated_target_balance = updated_target.get('balance', 0)

        await message.reply_text(
            f"🕵️ {html.escape(robber_name)} tried to rob {html.escape(target_name)}!\n\n"
            f"💸 {amount} coins have been transferred from {html.escape(robber_name)} to {html.escape(target_name)}.\n\n"
            f"Your new balance: {updated_robber_balance} coins\n"
            f"{html.escape(target_name)}'s new balance: {updated_target_balance} coins"
        )

        # Notify victim (best-effort)
        try:
            await client.send_message(
                chat_id=target_id,
                text=(
                    f"⚠️ You were targeted by {html.escape(robber_name)}'s /rob! "
                    f"You received {amount} coins.\nYour new balance: {updated_target_balance} coins"
                )
            )
        except Exception:
            pass

    except Exception as e:
        print(f"/rob error: {e}")
        await message.reply_text("An error occurred while processing /rob. Try again later.")
      
