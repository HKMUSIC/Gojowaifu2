from pyrogram import Client, filters
from pyrogram.types import Message
import random

@app.on_message(filters.command("brain"))
async def brain_cmd(client: Client, message: Message):

    # User must tag (reply) someone
    if not message.reply_to_message:
        return await message.reply(
            "Please reply to a user's message!\n\nExample:\nReply to someone and type:\n`/brain`"
        )

    target = message.reply_to_message.from_user
    percentage = random.randint(1, 100)

    # Output like screenshot
    text = f"""
🧠 **{target.first_name}'s Brain level:** {percentage}%
"""

    await message.reply(text)


@app.on_message(filters.command("looks"))
async def looks_cmd(client, message: Message):

    # user must reply/tag someone
    if not message.reply_to_message:
        return await message.reply(
            "Please reply to a user's message!\n\nExample:\nReply to someone and type:\n`/looks`"
        )

    target = message.reply_to_message.from_user

    # Random looks percentage
    looks = random.randint(1, 100)

    # Stylish output like KiddoBot
    text = f"""
😎 **{target.first_name}'s Looks level:** {looks}%
"""

    await message.reply(text)
