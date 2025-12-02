from TEAMZYRO import *
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import html, random, uuid
from datetime import datetime, timedelta

# ---------------- BALANCE HELPER ---------------- #
async def get_balance(user_id):
    user_data = await user_collection.find_one({'id': user_id}, {'balance': 1})
    if user_data:
        return user_data.get('balance', 0)
    return 0

# ---------------- BALANCE IMAGES ---------------- #
BALANCE_IMAGES = [
    "https://files.catbox.moe/3saw6n.jpg",
    "https://files.catbox.moe/3ilay5.jpg",
    "https://files.catbox.moe/i28al7.jpg",
    "https://files.catbox.moe/k7t6y7.jpg",
    "https://files.catbox.mo/h0ftuw.jpg",
    "https://files.catbox.moe/syanmk.jpg",
    "https://files.catbox.moe/shslw1.jpg",
    "https://files.catbox.moe/xokoit.jpg",
    "https://files.catbox.moe/6w5fl4.jpg"
]

# ---------------- BALANCE COMMAND ---------------- #
@app.on_message(filters.command("balance"))
async def balance(client: Client, message: Message):
    user_id = message.from_user.id
    user_balance = await get_balance(user_id)

    caption = (
        f"👤 {html.escape(message.from_user.first_name)}\n"
        f"💰 Balance: ||{user_balance} coins||"
    )

    photo_url = random.choice(BALANCE_IMAGES)

    await message.reply_photo(
        photo=photo_url,
        caption=caption,
        has_spoiler=True   
    )


@app.on_message(filters.command("pay"))
async def pay(client: Client, message: Message):
    sender_id = message.from_user.id
    args = message.command

    # Check args
    if len(args) < 2:
        return await message.reply_text("Usage: /pay <amount> [@username/user_id] or reply to a user.")

    # Validate amount
    try:
        amount = int(args[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        return await message.reply_text("❌ Invalid amount. Enter a positive number.")

    # Fetch sender data
    sender_data = await user_collection.find_one({'id': sender_id}) or {}
    if not sender_data:
        sender_data = {'id': sender_id, 'balance': 0, 'lockbalance': False}
        await user_collection.insert_one(sender_data)

    # Check sender lock
    if sender_data.get("lockbalance", False):
        return await message.reply_text("🔒 Your balance is locked! Use /unlockbalance to unlock it first.")

    # Identify recipient
    recipient_id = None
    recipient_name = None

    if message.reply_to_message:
        recipient_id = message.reply_to_message.from_user.id
        recipient_name = message.reply_to_message.from_user.first_name

    elif len(args) > 2:
        try:
            recipient_id = int(args[2])
        except ValueError:
            username = args[2].lstrip("@")
            user_data = await user_collection.find_one({'username': username})
            if user_data:
                recipient_id = user_data["id"]
                recipient_name = user_data.get("first_name", username)
            else:
                return await message.reply_text("❌ Recipient not found.")

    if not recipient_id:
        return await message.reply_text("❌ Recipient not found.")

    if recipient_id == sender_id:
        return await message.reply_text("❌ You cannot pay yourself.")

    # Fetch recipient data
    recipient_data = await user_collection.find_one({'id': recipient_id}) or {}
    if not recipient_data:
        recipient_data = {'id': recipient_id, 'balance': 0, 'lockbalance': False}
        await user_collection.insert_one(recipient_data)

    # Check recipient lock
    if recipient_data.get("lockbalance", False):
        return await message.reply_text(
            f"🔒 {recipient_name or 'This user'} has their balance locked!\n"
            f"Ask them to use /unlockbalance before receiving payments."
        )

    # Check balance
    if sender_data.get("balance", 0) < amount:
        return await message.reply_text("❌ Insufficient balance.")

    # Process transaction
    await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}})
    await user_collection.update_one({'id': recipient_id}, {'$inc': {'balance': amount}})

    new_sender_balance = sender_data.get("balance", 0) - amount
    new_recipient_balance = recipient_data.get("balance", 0) + amount

    sender_name = html.escape(message.from_user.first_name)
    recipient_disp = html.escape(recipient_name or str(recipient_id))

    # Notify sender
    await message.reply_text(
        f"✅ You paid {amount} coins to {recipient_disp}.\n"
        f"💰 Your New Balance: {new_sender_balance} coins"
    )

    # Notify recipient
    await client.send_message(
        chat_id=recipient_id,
        text=f"🎉 You received {amount} coins from {sender_name}!\n"
             f"💰 Your New Balance: {new_recipient_balance} coins"
    )
