import asyncio
import html
from pyrogram.types import Message
from random import choice, randint
from datetime import datetime, timedelta
from pyrogram import Client, filters

# database imports
from TEAMZYRO import ZYRO as bot, user_collection 
from TEAMZYRO import check_cooldown, get_remaining_cooldown  # optional if you use cooldown

last_challenges = {}  # store active challenges per chat
chat_message_count = {}     # counts messages per chat
spawn_interval = 30         # default: spawn every 30 messages

# ---------------- WAIFU CHALLENGE SYSTEM ---------------- #

@Client.on_message(filters.command("challenge_spawn"))
async def challenge_spawn(client: Client, message: Message):
    chat_id = message.chat.id

    # Fetch all waifus from DB
    all_chars = await characters_col.find().to_list(None)
    if not all_chars:
        return await message.reply_text("❌ No waifus available in database.")

    char = choice(all_chars)
    last_challenges[chat_id] = char  # store current waifu

    caption = (
        f"💫 A mysterious waifu has appeared! 💫\n\n"
        f"Type `/challenge {char['name']}` to fight her!"
    )

    try:
        await message.reply_photo(
            photo=char["image"],
            caption=caption,
            has_spoiler=True
        )
    except Exception as e:
        print("challenge_spawn error:", e)
        await message.reply_text("⚠️ Failed to send waifu image. Please check image URL.")


@Client.on_message(filters.command("challenge"))
async def challenge(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # optional: cooldown check
    if await check_cooldown(user_id):
        remaining_time = await get_remaining_cooldown(user_id)
        return await message.reply_text(
            f"⚠️ You're in cooldown. Try again in {remaining_time} seconds."
        )

    # Check if any waifu spawned in this chat
    if chat_id not in last_challenges:
        return await message.reply_text("❌ No waifu to challenge right now! Use /challenge_spawn first.")

    waifu = last_challenges[chat_id]
    guess = " ".join(message.command[1:]).strip().lower()

    if not guess:
        return await message.reply_text("Usage: `/challenge <character name>`", quote=True)

    # Compare guessed name
    if guess != waifu["name"].lower():
        return await message.reply_text("❌ Wrong challenge name! Try again.")

    # Remove current challenge from memory
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
            f"⚔️ {html.escape(user_name)} challenged {char_name}!\n"
            f"The fight was amazing — {char_name} was **{strength}**, but you emerged victorious! 🏆\n\n"
            f"💰 You won {reward} coins!"
        )
    else:
        await message.reply_text(
            f"⚔️ {html.escape(user_name)} challenged {char_name}!\n"
            f"The fight was intense — {char_name} was **{strength}**, and you lost this time. 😢\n"
            f"Better luck next challenge!"
        )
        
@Client.on_message(filters.group | filters.private)
async def auto_spawn(client: Client, message: Message):
    chat_id = message.chat.id

    # Increment message count
    if chat_id not in chat_message_count:
        chat_message_count[chat_id] = 0
    chat_message_count[chat_id] += 1

    # Check if interval reached
    if chat_message_count[chat_id] >= spawn_interval:
        chat_message_count[chat_id] = 0  # reset counter
        await challenge_spawn(client, message)  # call spawn function

@Client.on_message(filters.command("settime"))
async def set_time(client: Client, message: Message):
    global spawn_interval
    try:
        new_interval = int(message.command[1])
        if new_interval < 1:
            return await message.reply_text("❌ Interval must be at least 1 message.")
        spawn_interval = new_interval
        await message.reply_text(f"✅ Waifu will now spawn every {spawn_interval} messages.")
    except:
        await message.reply_text("❌ Usage: /settime <number>")




# ---------------- ROB COMMAND (REPLY ONLY, DAILY LIMIT + COOLDOWN) ---------------- #

COOLDOWN_SECONDS = 120 # 1 minute cooldown between robs

@Client.on_message(filters.command("rob") & (filters.group | filters.private))
async def rob_command(client: Client, message):
    try:
        # Must reply to a user's message
        if not message.reply_to_message or not message.reply_to_message.from_user:
            await message.reply_text("❌ Reply to a user's message with /rob to rob them.")
            return

        robber_id = message.from_user.id
        robber_name = message.from_user.first_name or str(robber_id)

        target = message.reply_to_message.from_user
        target_id = target.id
        target_name = target.first_name or str(target_id)

        # Prevent robbing self or bot
        if target_id == robber_id:
            await message.reply_text("😅 You cannot rob yourself.")
            return

        bot_id = (await client.get_me()).id
        if target_id == bot_id or robber_id == bot_id:
            await message.reply_text("❌ You cannot rob the bot.")
            return

        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        # ---------------- Ensure robber exists ---------------- #
        robber_doc = await user_collection.find_one({'id': robber_id})
        if not robber_doc:
            await user_collection.insert_one({
                'id': robber_id,
                'username': message.from_user.username,
                'first_name': message.from_user.first_name,
                'balance': 0,
                'rob_today': 0,
                'rob_day': today_str,
                'last_rob': None
            })
            robber_doc = {'id': robber_id, 'balance': 0, 'rob_today': 0, 'rob_day': today_str, 'last_rob': None}

        # Reset daily count if day changed
        if robber_doc.get('rob_day') != today_str:
            await user_collection.update_one(
                {'id': robber_id},
                {'$set': {'rob_today': 0, 'rob_day': today_str}}
            )
            robber_doc['rob_today'] = 0
            robber_doc['rob_day'] = today_str

        # ---------------- Check daily limit ---------------- #
        if robber_doc.get('rob_today', 0) >= 5:
            await message.reply_text("⚠️ You can only use /rob **5 times per day**. Try again tomorrow.")
            return

        # ---------------- Check cooldown ---------------- #
        last_rob_time = robber_doc.get('last_rob')
        if last_rob_time:
            last_rob_dt = datetime.strptime(last_rob_time, "%Y-%m-%d %H:%M:%S")
            diff = datetime.utcnow() - last_rob_dt
            if diff.total_seconds() < COOLDOWN_SECONDS:
                remaining = int(COOLDOWN_SECONDS - diff.total_seconds())
                await message.reply_text(f"⏳ You are on cooldown. Try again in {remaining} seconds.")
                return

        # ---------------- Ensure target exists ---------------- #
        target_doc = await user_collection.find_one({'id': target_id})
        if not target_doc:
            await user_collection.insert_one({
                'id': target_id,
                'username': getattr(target, 'username', None),
                'first_name': getattr(target, 'first_name', None),
                'balance': 0
            })
            target_doc = {'id': target_id, 'balance': 0}

        # ---------------- Perform rob ---------------- #
        amount = randint(50, 90)
        robber_balance = robber_doc.get('balance', 0)

        if robber_balance < amount:
            await message.reply_text(
                f"❌ Insufficient balance. You need {amount} coins but you have {robber_balance}."
            )
            return

        # Update balances and rob stats
        await user_collection.update_one(
            {'id': robber_id},
            {'$inc': {'balance': -amount, 'rob_today': 1},
             '$set': {'last_rob': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}}
        )
        await user_collection.update_one(
            {'id': target_id},
            {'$inc': {'balance': amount}}
        )

        # Fetch updated balances
        updated_robber = await user_collection.find_one({'id': robber_id})
        updated_target = await user_collection.find_one({'id': target_id})

        await message.reply_text(
            f"🕵️ {html.escape(robber_name)} robbed {html.escape(target_name)}!\n\n"
            f"💸 {amount} coins transferred.\n\n"
            f"Your new balance: {updated_robber.get('balance', 0)} coins\n"
            f"{html.escape(target_name)}'s new balance: {updated_target.get('balance', 0)} coins\n"
            f"🗓 You have used /rob {updated_robber.get('rob_today',0)}/5 times today."
        )

        # Notify victim
        try:
            await client.send_message(
                chat_id=target_id,
                text=(
                    f"⚠️ You were robbed by {html.escape(robber_name)}!\n"
                    f"You received {amount} coins.\n"
                    f"Your new balance: {updated_target.get('balance', 0)} coins"
                )
            )
        except:
            pass

    except Exception as e:
        print(f"/rob error: {e}")
        await message.reply_text("❌ An error occurred while processing /rob. Try again later.")


