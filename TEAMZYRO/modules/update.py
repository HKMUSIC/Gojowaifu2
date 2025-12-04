from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import ReturnDocument
from TEAMZYRO import collection, SUDO, app, user_collection, require_power
from TEAMZYRO.unit.zyro_rarity import rarity_map
import asyncio

SUDO_USERS = SUDO


# ======================================================
# DELETE CHARACTER
# ======================================================
@app.on_message(filters.command("delete"))
@require_power("delete_character")
async def delete_handler(client, message):
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.reply_text("Incorrect format... Please use: /delete ID")
            return

        character_id = args[1]
        character = await collection.find_one_and_delete({'id': character_id})

        if character:
            update_result = await user_collection.update_many(
                {'characters.id': character_id},
                {'$pull': {'characters': {'id': character_id}}}
            )
            await message.reply_text(
                f"Character {character_id} deleted successfully.\n"
                f"Removed from {update_result.modified_count} users."
            )
        else:
            await message.reply_text("Character not found.")

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")


# ======================================================
# UPDATE SINGLE CHARACTER
# ======================================================
@app.on_message(filters.command("update"))
@require_power("update_character")
async def update(client: Client, message: Message):
    try:
        args = message.text.split()
        if len(args) != 4:
            await message.reply_text("Use: /update id field new_value")
            return

        character_id = args[1]
        field = args[2]
        new_value = args[3]

        valid_fields = ['img_url', 'name', 'anime', 'rarity']
        if field not in valid_fields:
            await message.reply_text(f"Invalid field. Use: {', '.join(valid_fields)}")
            return

        if field in ["name", "anime"]:
            new_value = new_value.replace("-", " ").title()
        elif field == "rarity":
            try:
                new_value = rarity_map[int(new_value)]
            except:
                await message.reply_text("Invalid rarity (1–12).")
                return

        result = await collection.update_one({'id': character_id}, {'$set': {field: new_value}})
        if result.modified_count == 0:
            await message.reply_text("Character not found or no change made.")
            return

        users = user_collection.find({'characters.id': character_id})
        total_users = await user_collection.count_documents({'characters.id': character_id})

        if total_users == 0:
            await message.reply_text("Updated successfully.")
            return

        progress = await message.reply_text("Updating: 0%...")
        done = 0
        next_step = 10

        async for user in users:
            await user_collection.update_one(
                {'_id': user['_id'], 'characters.id': character_id},
                {'$set': {f"characters.$.{field}": new_value}}
            )
            done += 1

            percent = (done / total_users) * 100
            if percent >= next_step:
                await progress.edit_text(f"Updating: {int(percent)}%")
                next_step += 10
                await asyncio.sleep(1)

        await progress.edit_text("Updating: 100% completed.")
        await message.reply_text(f"Updated users: {done}/{total_users}")

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")


# ======================================================
# MAX UPDATE (MULTIPLE ID UPDATE)
# ======================================================
@app.on_message(filters.command("maxupdate"))
@require_power("update_character")
async def update_multiple(client: Client, message: Message):
    try:
        args = message.text.split()
        if len(args) < 4:
            await message.reply_text("Use: /maxupdate id1,id2,id3 field value")
            return

        ids = args[1].split(",")
        field = args[2]
        new_value = " ".join(args[3:])

        valid_fields = ['img_url', 'vid_url', 'name', 'anime', 'rarity']
        if field not in valid_fields:
            await message.reply_text(f"Invalid field. Use: {', '.join(valid_fields)}")
            return

        if field in ["name", "anime"]:
            new_value = new_value.replace("-", " ").title()
        elif field == "rarity":
            try:
                new_value = rarity_map[int(new_value)]
            except:
                await message.reply_text("Invalid rarity.")
                return

        total = len(ids)
        done_chars = 0
        updated_users = 0

        progress = await message.reply_text("Updating: 0% ...")
        next_step = 10

        for i, cid in enumerate(ids, 1):

            result = await collection.update_one({'id': cid}, {'$set': {field: new_value}})
            if result.modified_count == 0:
                continue

            users = user_collection.find({'characters.id': cid})

            async for u in users:
                await user_collection.update_one(
                    {'_id': u['_id'], 'characters.id': cid},
                    {'$set': {f"characters.$.{field}": new_value}}
                )
                updated_users += 1

            done_chars += 1

            percent = (i / total) * 100
            if percent >= next_step:
                await progress.edit_text(f"Updating: {int(percent)}%")
                next_step += 10
                await asyncio.sleep(1)

        await progress.edit_text("Updating: 100%.")
        await message.reply_text(
            f"Characters updated: {done_chars}/{total}\n"
            f"Users updated: {updated_users}"
        )

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")


# ======================================================
# FIND BY ANIME NAME
# ======================================================
@app.on_message(filters.command("findani") & filters.user(SUDO_USERS))
async def find_anime_ids(client: Client, message: Message):
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Usage: /findani anime-name")
            return

        anime = args[1].lower().strip()
        cursor = collection.find({"anime": {"$regex": anime, "$options": "i"}}, {"id": 1})

        ids = [c["id"] for c in await cursor.to_list(None)]

        if not ids:
            await message.reply_text("No characters found.")
        else:
            await message.reply_text("IDs:\n" + ",".join(ids))

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")


# ======================================================
# NEW COMMAND: FIND BY NAME
# ======================================================
@app.on_message(filters.command("findname") & filters.user(SUDO_USERS))
async def find_by_name(client, message):
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text("Usage: /findname name")
            return

        name = args[1].lower()

        cursor = collection.find({"name": {"$regex": name, "$options": "i"}}, {"id": 1})
        ids = [c["id"] for c in await cursor.to_list(None)]

        if not ids:
            await message.reply_text("No character found.")
        else:
            await message.reply_text("IDs:\n" + ",".join(ids))

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")


# ======================================================
# NEW COMMAND: FIND BY RARITY
# ======================================================
@app.on_message(filters.command("findrarity") & filters.user(SUDO_USERS))
async def find_by_rarity(client, message):
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.reply_text("Usage: /findrarity number(1-12)")
            return

        try:
            rarity = rarity_map[int(args[1])]
        except:
            await message.reply_text("Invalid rarity number.")
            return

        cursor = collection.find({"rarity": rarity}, {"id": 1})
        ids = [c["id"] for c in await cursor.to_list(None)]

        await message.reply_text("IDs:\n" + ",".join(ids) if ids else "No characters found.")

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")


# ======================================================
# NEW COMMAND: REMOVE DUPLICATE CARDS FROM ALL USERS
# ======================================================
@app.on_message(filters.command("duplifix") & filters.user(SUDO_USERS))
async def remove_duplicates(client, message):
    try:
        users = user_collection.find({})
        fixed = 0

        async for u in users:
            chars = u.get("characters", [])
            unique = {c["id"]: c for c in chars}
            if len(unique) != len(chars):
                await user_collection.update_one(
                    {"_id": u["_id"]},
                    {"$set": {"characters": list(unique.values())}}
                )
                fixed += 1

        await message.reply_text(f"Duplicate fix completed.\nUsers fixed: {fixed}")

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")


# ======================================================
# NEW COMMAND: FIX USER DATABASE
# ======================================================
@app.on_message(filters.command("fixuserdb") & filters.user(SUDO_USERS))
async def fix_user_db(client, message):
    try:
        users = user_collection.find({})
        fixed = 0

        async for u in users:
            updated = False
            new_list = []

            for c in u.get("characters", []):
                if not {"id", "name", "anime", "img_url", "rarity"} <= c.keys():
                    main = await collection.find_one({"id": c["id"]})
                    if main:
                        new_list.append(main)
                        updated = True
                    continue

                new_list.append(c)

            if updated:
                await user_collection.update_one({"_id": u["_id"]}, {"$set": {"characters": new_list}})
                fixed += 1

        await message.reply_text(f"User DB fixed.\nUsers updated: {fixed}")

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")
