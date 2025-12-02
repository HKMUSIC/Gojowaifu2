from TEAMZYRO import app
from pyrogram import filters
from pyrogram.types import Message
import random

@app.on_message(filters.command("brain"))
async def brain_cmd(client, message: Message):

    if not message.reply_to_message:
        return await message.reply(
            "Please reply to a user's message!\n\nExample:\nReply to someone and type:\n`/brain`"
        )

    target = message.reply_to_message.from_user
    percentage = random.randint(1, 100)

    text = f"""
🧠 **{target.first_name}'s Brain level:** {percentage}%
"""
    await message.reply(text)


@app.on_message(filters.command("looks"))
async def looks_cmd(client, message: Message):

    if not message.reply_to_message:
        return await message.reply(
            "Please reply to a user's message!\n\nExample:\nReply to someone and type:\n`/looks`"
        )

    target = message.reply_to_message.from_user
    looks = random.randint(1, 100)

    text = f"""
😎 **{target.first_name}'s Looks level:** {looks}%
"""
    await message.reply(text)

@app.on_message(filters.command("love"))
async def looks_cmd(client, message: Message):

    if not message.reply_to_message:
        return await message.reply(
            "Please reply to a user's message!\n\nExample:\nReply to someone and type:\n`/love`"
        )

    target = message.reply_to_message.from_user
    loves = random.randint(1, 100)

    text = f"""
❤️ **{target.first_name}'s Loves level:** {loves}%
"""
    await message.reply(text)
