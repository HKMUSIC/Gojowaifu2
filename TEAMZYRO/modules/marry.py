import asyncio
from datetime import datetime, timedelta
from pyrogram import filters, types as t
from TEAMZYRO import ZYRO as bot
from TEAMZYRO import user_collection, collection

# Cooldown cache
marry_lock = {}


@bot.on_message(filters.command("marry"))
async def marry_cmd(_, message: t.Message):
    user_id = message.from_user.id
    mention = message.from_user.mention

    try:
        # ----- Fetch or Create User -----
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

        # ----- Cooldown Check (10 min) -----
        last_marry = user_data.get("last_marry_time")
        if last_marry:
            elapsed = datetime.utcnow() - last_marry
            if elapsed < timedelta(minutes=10):
                remaining = timedelta(minutes=10) - elapsed
                mins = int(remaining.total_seconds() // 60)
                secs = int(remaining.total_seconds() % 60)
                return await message.reply_text(
                    f"⏳ **Wait `{mins}m {secs}s` before using /marry again.**"
                )

        # ----- Dice Animation -----
        dice_msg = await message.reply_dice("💘")
        await asyncio.sleep(2)

        # ----- Pick Random Character -----
        pipeline = [{"$sample": {"size": 1}}]
        cursor = collection.aggregate(pipeline)
        characters = await cursor.to_list(length=1)

        if not characters:
            return await message.reply_text("❌ No characters available right now!")

        char = characters[0]

        # ----- Update Marry Time -----
        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"last_marry_time": datetime.utcnow()}}
        )

        # ----- Send Character Photo -----
        caption = (
            f"🎉 **ᴄᴏɴɢʀᴀᴛᴜʟᴀᴛɪᴏɴꜱ! {mention}** 🎉\n"
            f"**ʏᴏᴜ ᴀʀᴇ ɴᴏᴡ ᴍᴀʀʀɪᴇᴅ! ʜᴇʀᴇ ɪꜱ ʏᴏᴜʀ ᴄʜᴀʀᴀᴄᴛᴇʀ:**\n\n"
            f"👰 **Name:** `{char['name']}`\n"
            f"⭐ **Rarity:** `{char['rarity']}`\n"
            f"📺 **Anime:** `{char['anime']}`"
        )

        await message.reply_photo(photo=char["img_url"], caption=caption)

    except Exception as e:
        print("MARRY ERROR:", e)
        await message.reply_text("❌ Something went wrong in /marry!")
