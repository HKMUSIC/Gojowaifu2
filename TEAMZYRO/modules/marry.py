import asyncio
from pyrogram import Client, filters, types as t
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from TEAMZYRO import ZYRO as bot
from TEAMZYRO import user_collection, collection  # <-- both pymongo


@bot.on_message(filters.command(["marry"]))
async def marry_cmd(_, message: t.Message):
    user_id = message.from_user.id
    mention = message.from_user.mention

    try:
        # Fetch user
        user_data = user_collection.find_one({"id": user_id})

        if not user_data:
            user_data = {
                "id": user_id,
                "username": message.from_user.username,
                "characters": [],
                "last_daily_reward": None,
                "last_marry_time": None
            }
            user_collection.insert_one(user_data)

        # Cooldown (10 minutes)
        last_marry = user_data.get("last_marry_time")

        if last_marry:
            elapsed = datetime.utcnow() - last_marry
            if elapsed < timedelta(minutes=10):
                remaining = timedelta(minutes=10) - elapsed
                mins = int(remaining.total_seconds() // 60)
                secs = int(remaining.total_seconds() % 60)
                return await message.reply_text(
                    f"⏳ **You must wait `{mins}m {secs}s` before using /marry again!**"
                )

        # Send dice
        await message.reply_dice("🎲")
        await asyncio.sleep(2)

        # Random waifu using PyMongo (sync aggregate)
        pipeline = [{"$sample": {"size": 1}}]
        characters = list(collection.aggregate(pipeline))

        if not characters:
            return await message.reply_text("❌ No characters found!")

        char = characters[0]

        # Prepare caption
        caption = (
            f"🎉 **CONGRATULATIONS! {mention}** 🎉\n"
            f"You are now *MARRIED!* 💍\n\n"
            f"👰 **Character:** `{char['name']}`\n"
            f"⭐ **Rarity:** `{char['rarity']}`\n"
            f"📺 **Anime:** `{char['anime']}`"
        )

        # Send image + caption
        await message.reply_photo(photo=char['img_url'], caption=caption)

        # Update marry time
        user_collection.update_one(
            {"id": user_id},
            {"$set": {"last_marry_time": datetime.utcnow()}}
        )

    except Exception as e:
        print("Error in marry command:", e)
        await message.reply_text("❌ Something went wrong in /marry!")
