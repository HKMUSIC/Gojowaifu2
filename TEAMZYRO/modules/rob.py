from TEAMZYRO import ZYRO as bot
from TEAMZYRO import user_collection
from pyrogram import filters
from pyrogram.types import Message
import random

@bot.on_message(filters.command("rob"))
async def rob_cmd(_, message: Message):

    # Must reply to someone
    if not message.reply_to_message:
        return await message.reply("❗ Reply to a user!\nUsage:\n/rob [reply] [amount]")

    target = message.reply_to_message.from_user
    robber = message.from_user

    # Amount required
    try:
        amount = int(message.command[1])
    except:
        return await message.reply("❗ Enter a valid amount!\nUsage:\n/rob [reply] [amount]")

    if amount < 1 or amount > 100000:
        return await message.reply("⚠ Amount must be between **1–100000**.")

    # Fetch robber + target data
    robber_data = await user_collection.find_one({"id": robber.id})
    target_data = await user_collection.find_one({"id": target.id})

    # Create user if not exist
    if not robber_data:
        robber_data = {"id": robber.id, "balance": 0, "lockbalance": False}
        await user_collection.insert_one(robber_data)

    if not target_data:
        target_data = {"id": target.id, "balance": 0, "lockbalance": False}
        await user_collection.insert_one(target_data)

    # Target lock check
    if target_data.get("lockbalance"):
        return await message.reply(f"🔒 **{target.first_name}'s balance is locked. You can't rob!**")

    # Low balance check
    if target_data["balance"] < amount:
        return await message.reply(
            f"😅 - {target.first_name} only has **${target_data['balance']}**.\nYou must ask for less!"
        )

    # Rob success/fail chance
    success = random.randint(1, 100)

    if success <= 50:
        # SUCCESS — money transfer
        await user_collection.update_one(
            {"id": target.id},
            {"$inc": {"balance": -amount}}
        )
        await user_collection.update_one(
            {"id": robber.id},
            {"$inc": {"balance": amount}}
        )

        return await message.reply(
            f"💰 **Robbery Successful!**\n"
            f"{robber.first_name} stole **${amount}** from {target.first_name}!"
        )

    else:
        # FAIL — robber pays fine
        fine = int(amount * 0.30)  # 30% fine

        await user_collection.update_one(
            {"id": robber.id},
            {"$inc": {"balance": -fine}}
        )
        await user_collection.update_one(
            {"id": target.id},
            {"$inc": {"balance": fine}}
        )

        return await message.reply(
            f"🚨 **Robbery Failed!**\n"
            f"{robber.first_name} paid **${fine}** as penalty to {target.first_name}!"
        )



@bot.on_message(filters.command("unlockbalance"))
async def unlock_balance_cmd(_, message: Message):
    user_id = message.from_user.id

    # Find user
    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await message.reply("❌ You don't have an account yet!")

    # If already unlocked
    if not user.get("lockbalance", False):
        return await message.reply("🔓 Your balance is already unlocked!")

    # Unlock the balance
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"lockbalance": False}}
    )

    await message.reply("🔓 **Your balance has been unlocked!**")


@bot.on_message(filters.command("lockbalance"))
async def lock_balance_cmd(_, message: Message):
    user_id = message.from_user.id

    # Find user
    user = await user_collection.find_one({"id": user_id})
    if not user:
        return await message.reply("❌ You don't have an account yet!")

    # If already locked
    if user.get("lockbalance", False):
        return await message.reply("🔒 Your balance is already locked!")

    # Lock the balance
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"lockbalance": True}}
    )

    await message.reply("🔒 **Your balance has been locked!**")
