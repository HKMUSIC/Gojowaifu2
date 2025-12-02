import asyncio
from datetime import datetime, timedelta
from pyrogram import filters, types as t
from TEAMZYRO import ZYRO as bot
from TEAMZYRO import user_collection, collection   # SAME DB like hclaim


@bot.on_message(filters.command(["marry"]))
async def marry_cmd(_, message: t.Message):
    user_id = message.from_user.id
    mention = message.from_user.mention

    try:
        # Fetch user data (async, same as hclaim)
        user_data = await user_collection.find_one({"id": user_id})

        if not user_data:
            user_data = {
                "id": user_id,
                "username": message.from_user.username,
                "characters": [],
                "last_daily_reward": None,
                "last_marry_time": None
            }
            await user_collection.insert_one(user_data)

        # Cooldown 10 mins
        last_marry = user_data.get("last_marry_time")

        if last_marry:
            elapsed = datetime.utcnow() - last_marry
            if elapsed < timedelta(minutes=10):
                rem = timedelta(minutes=10) - elapsed
                mins = int(rem.total_seconds() // 60)
                secs = int(rem.total_seconds() % 60)
                return await message.reply_text(
                    f"⏳ **Please wait `{mins}m {secs}s` before using /marry again!**"
                )

        # Send dice
        await message.reply_dice("🎲")
        await asyncio.sleep(2)

        # Fetch random character (EXACT SAME AS hclaim)
        pipeline = [
            {"$sample": {"size": 1}}
        ]
        cursor = collection.aggregate(pipeline)
        characters = await cursor.to_list(length=1)

        if not characters:
            return await message.reply_text("❌ No characters found!")

        char = characters[0]

        caption = (
            f"💍 **CONGRATULATIONS {mention}!** 💍\n"
            f"You're now *MARRIED* 🎉\n\n"
            f"👰 **Name:** {char['name']}\n"
            f"⭐ **Rarity:** {char['rarity']}\n"
            f"🎬 **Anime:** {char['anime']}\n"
        )

        # Send photo
        await message.reply_photo(photo=char["img_url"], caption=caption)

        # Update marry cooldown time
        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"last_marry_time": datetime.utcnow()}}
        )
