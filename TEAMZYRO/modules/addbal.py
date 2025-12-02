from TEAMZYRO import app
from pyrogram import filters
from pyrogram.types import Message

OWNER_ID = 7553434931  # <- Apna ID lagao


# --------------------- ADD MONEY ---------------------
@app.on_message(filters.command("addmoney"))
async def add_money(client, message: Message):

    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ You are not allowed to use this command!")

    if not message.reply_to_message:
        return await message.reply("❌ Tag a user by replying!\nExample: reply → /addmoney 100")

    # amount
    args = message.command
    if len(args) < 2:
        return await message.reply("❌ Enter amount also!")

    try:
        amount = int(args[1])
        if amount <= 0:
            raise ValueError
    except:
        return await message.reply("❌ Invalid amount!")

    target = message.reply_to_message.from_user
    user_id = target.id

    # ensure user exists
    user = await user_collection.find_one({"id": user_id})
    if not user:
        await user_collection.insert_one({"id": user_id, "balance": 0})

    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": amount}}
    )

    updated = await user_collection.find_one({"id": user_id})

    await message.reply(
        f"💰 Added <b>{amount}</b> coins to <a href='tg://user?id={user_id}'>{target.first_name}</a>\n"
        f"🧾 New Balance: <b>{updated['balance']}</b>",
        parse_mode="html"
    )


# --------------------- REMOVE MONEY ---------------------
@app.on_message(filters.command("removemoney"))
async def remove_money(client, message: Message):

    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ You are not allowed to use this command!")

    if not message.reply_to_message:
        return await message.reply("❌ Tag a user by replying!\nExample: reply → /removemoney 100")

    # amount
    args = message.command
    if len(args) < 2:
        return await message.reply("❌ Enter amount also!")

    try:
        amount = int(args[1])
        if amount <= 0:
            raise ValueError
    except:
        return await message.reply("❌ Invalid amount!")

    target = message.reply_to_message.from_user
    user_id = target.id

    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await message.reply("❌ User has no account!")

    # Negative balance check
    if user["balance"] < amount:
        return await message.reply("❌ Not enough balance to remove!")

    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": -amount}}
    )

    updated = await user_collection.find_one({"id": user_id})

    await message.reply(
        f"💸 Removed <b>{amount}</b> coins from <a href='tg://user?id={user_id}'>{target.first_name}</a>\n"
        f"🧾 New Balance: <b>{updated['balance']}</b>",
        parse_mode="html"
  )
