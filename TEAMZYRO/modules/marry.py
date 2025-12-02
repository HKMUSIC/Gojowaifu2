from pyrogram import Client, filters
from datetime import datetime, timedelta
import asyncio

# ---- Mongo Collections ----
from TEAMZYRO import ZYRO as bot
from TEAMZYRO import users   # <== make sure this is your Mongo collection


@bot.on_message(filters.command("marry"))
async def marry_cmd(client, message):

    try:
        user_id = message.from_user.id
        
        # ---------------------------------------
        # Fetch user or create if doesn't exist
        # ---------------------------------------
        user = users.find_one({"_id": user_id})

        if user is None:
            users.insert_one({
                "_id": user_id,
                "marry_cooldown": None
            })
            user = users.find_one({"_id": user_id})

        # ---------------------------------------
        # Cooldown check
        # ---------------------------------------
        last_marry = user.get("marry_cooldown")

        if last_marry:
            remaining = datetime.utcnow() - last_marry
            if remaining < timedelta(minutes=10):
                wait = timedelta(minutes=10) - remaining
                mins = int(wait.total_seconds() // 60)
                secs = int(wait.total_seconds() % 60)

                return await message.reply_text(
                    f"⏳ **Wait `{mins}m {secs}s` before using /marry again!**"
                )

        # ---------------------------------------
        # Send dice animation
        # ---------------------------------------
        dice = await message.reply_dice("💘")
        await asyncio.sleep(3)

        value = dice.dice.value

        # ---------------------------------------
        # Store new cooldown
        # ---------------------------------------
        users.update_one(
            {"_id": user_id},
            {"$set": {"marry_cooldown": datetime.utcnow()}}
        )

        # ---------------------------------------
        # Dice result message
        # ---------------------------------------
        if value >= 5:
            await message.reply_text("💍 **Congratulations! You got married!**")
        else:
            await message.reply_text("💔 **Marriage failed… Try again after cooldown.**")

    except Exception as e:
        # Print real error (for debugging)
        print("MARRY ERROR:", e)

        # User-friendly message
        await message.reply_text("❌ Unexpected error, but bot is safe.")
