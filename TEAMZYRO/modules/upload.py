import os
import requests
import asyncio
from pyrogram import filters
from TEAMZYRO import (
    application,
    CHARA_CHANNEL_ID,
    SUPPORT_CHAT,
    OWNER_ID,
    collection,
    user_collection,
    db,
    SUDO,
    rarity_map,
    ZYRO,
    require_power
)

# Wrong format instruction (kept same)
WRONG_FORMAT_TEXT = """Wrong ❌ format...  eg. /upload reply to photo muzan-kibutsuji Demon-slayer 3

format:- /upload reply character-name anime-name rarity-number

use rarity number accordingly rarity Map

rarity_map = {
    1: "⚪️ Low",
    2: "🟠 Medium",
    3: "🔴 High",
    4: "🎩 Special Edition",
    5: "🪽 Elite Edition",
    6: "🪐 Exclusive",
    7: "💞 Valentine",
    8: "🎃 Halloween",
    9: "❄️ Winter",
    10: "🏖 Summer",
    11: "🎗 Royal",
    12: "💸 Luxury Edition",
    13: "🍃 echhi",
    14: "🌧️ Rainy Edition",
    15: "🎍 Festival"
}
"""

# Find next available ID (works for motor collections)
async def find_available_id():
    cursor = collection.find().sort("id", 1)
    ids = []
    async for doc in cursor:
        if "id" in doc:
            try:
                ids.append(int(doc["id"]))
            except Exception:
                # skip non-numeric IDs (or handle differently)
                continue
    ids.sort()
    for i in range(1, len(ids) + 2):
        if i not in ids:
            return str(i).zfill(2)
    return str(len(ids) + 1).zfill(2)

# Upload to Catbox (file_path required)
def upload_to_catbox(file_path):
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError("file_path is missing or file does not exist")

    url = "https://catbox.moe/user/api.php"
    with open(file_path, "rb") as file:
        response = requests.post(
            url,
            data={"reqtype": "fileupload"},
            files={"fileToUpload": file},
            timeout=60
        )
    if response.status_code == 200 and response.text.startswith("https"):
        return response.text.strip()
    else:
        raise Exception(f"Error uploading to Catbox: {response.status_code} {response.text}")

upload_lock = asyncio.Lock()

@ZYRO.on_message(filters.command(["upload"]))
@require_power("add_character")
async def ul(client, message):
    """
    /upload handler:
    Usage: reply to photo/document/video with:
        /upload character-name anime-name rarity-number
    character-name and anime-name are hyphen-separated words (muzen-kibutsuji -> Muzan Kibutsuji)
    """
    global upload_lock

    if upload_lock.locked():
        return await message.reply_text("Another upload is in progress. Please wait until it is completed.")

    async with upload_lock:
        reply = message.reply_to_message
        if not reply:
            return await message.reply_text("Please reply to a photo, document, or video with the /upload command.")

        # Basic args parsing
        args = message.text.strip().split()
        if len(args) != 4:
            return await client.send_message(chat_id=message.chat.id, text=WRONG_FORMAT_TEXT)

        try:
            character_name = args[1].replace('-', ' ').title()
            anime = args[2].replace('-', ' ').title()
            rarity = int(args[3])
        except Exception:
            return await message.reply_text("Invalid command format. Check /upload usage.")

        if rarity not in rarity_map:
            return await message.reply_text("Invalid rarity value. Please use a valid one from the rarity map.")

        rarity_text = rarity_map[rarity]
        available_id = await find_available_id()

        character = {
            'name': character_name,
            'anime': anime,
            'rarity': rarity_text,
            'rarity_number': rarity,
            'id': available_id
        }

        processing_message = await message.reply_text("ᴜᴘʟᴏᴀᴅɪɴɢ....")
        path = None
        thumb_path = None
        try:
            # Download the replied media to a temp path
            path = await reply.download()
            if not path or not os.path.exists(path):
                raise Exception("Failed to download media.")

            # Upload main file to Catbox
            catbox_url = upload_to_catbox(path)

            # assign correct url field
            if reply.photo or reply.document:
                character['img_url'] = catbox_url
            elif reply.video:
                character['vid_url'] = catbox_url
                # try to download thumbnail if present
                try:
                    thumbs = getattr(reply.video, "thumbs", None)
                    if thumbs and len(thumbs) > 0:
                        thumb_path = await client.download_media(thumbs[0].file_id)
                        if thumb_path and os.path.exists(thumb_path):
                            thumbnail_url = upload_to_catbox(thumb_path)
                            character['thum_url'] = thumbnail_url
                except Exception:
                    # non-fatal, continue without thumbnail
                    pass

            caption_text = (
                f"Character Name: {character_name}\n"
                f"Anime Name: {anime}\n"
                f"Rarity: {rarity_text}\n"
                f"ID: {available_id}\n"
                f"Added by [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
            )

            # send to CHARA channel
            if 'img_url' in character:
                await client.send_photo(chat_id=CHARA_CHANNEL_ID, photo=character['img_url'], caption=caption_text)
            elif 'vid_url' in character:
                await client.send_video(chat_id=CHARA_CHANNEL_ID, video=character['vid_url'], caption=caption_text)
            else:
                # fallback: send the local file if remote URL unknown
                await client.send_document(chat_id=CHARA_CHANNEL_ID, document=path, caption=caption_text)

            # insert into DB
            await collection.insert_one(character)

            await message.reply_text(
                f"➲ ᴀᴅᴅᴇᴅ ʙʏ» [{message.from_user.first_name}](tg://user?id={message.from_user.id})\n"
                f"➥ Character ID: {available_id}\n"
                f"➥ Rarity: {rarity_text}\n"
                f"➥ Character Name: {character_name}"
            )
        except Exception as e:
            await message.reply_text(f"Character Upload Unsuccessful. Error: {str(e)}")
        finally:
            # cleanup downloaded files (if exist)
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
            try:
                if thumb_path and os.path.exists(thumb_path):
                    os.remove(thumb_path)
            except Exception:
                pass
            # remove the temporary processing message if exists
            try:
                await processing_message.delete()
            except Exception:
                pass
