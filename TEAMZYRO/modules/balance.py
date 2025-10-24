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

    if len(args) < 2:
        await message.reply_text("Usage: /pay <amount> [@username/user_id] or reply to a user.")
        return

    try:
        amount = int(args[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("Invalid amount. Please enter a positive number.")
        return

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
            recipient_username = args[2].lstrip('@')
            user_data = await user_collection.find_one({'username': recipient_username}, {'id': 1, 'first_name': 1})
            if user_data:
                recipient_id = user_data['id']
                recipient_name = user_data.get('first_name', recipient_username)
            else:
                await message.reply_text("Recipient not found.")
                return

    if not recipient_id:
        await message.reply_text("Recipient not found. Reply to a user or provide a valid user ID/username.")
        return

    # Ensure both users exist in DB
    for uid in [sender_id, recipient_id]:
        if not await user_collection.find_one({'id': uid}):
            await user_collection.insert_one({'id': uid, 'balance': 0})

    sender_balance = await get_balance(sender_id)
    if sender_balance < amount:
        await message.reply_text("❌ Insufficient balance.")
        return

    await user_collection.update_one({'id': sender_id}, {'$inc': {'balance': -amount}})
    await user_collection.update_one({'id': recipient_id}, {'$inc': {'balance': amount}})

    updated_sender_balance = await get_balance(sender_id)
    updated_recipient_balance = await get_balance(recipient_id)

    recipient_display = html.escape(recipient_name or str(recipient_id))
    sender_display = html.escape(message.from_user.first_name or str(sender_id))

    await message.reply_text(
        f"✅ You paid {amount} coins to {recipient_display}.\n"
        f"💰 Your New Balance: {updated_sender_balance} coins"
    )

    await client.send_message(
        chat_id=recipient_id,
        text=f"🎉 You received {amount} coins from {sender_display}!\n"
             f"💰 Your New Balance: {updated_recipient_balance} coins"
        )


@app.on_message(filters.command("kill"))
async def kill_handler(client, message):
    try:
        print("Kill command triggered")  # Log
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
        else:
            await message.reply_text("Please reply to a user's message to use /kill.")
            return

        command_args = message.text.split()
        if len(command_args) < 2:
            await message.reply_text("Please specify an option: c / f / b.")
            return

        option = command_args[1]
        user_exists = await user_collection.find_one({"id": user_id})
        if not user_exists:
            await message.reply_text("User not found in DB.")
            return

        if option == "f":
            await user_collection.delete_one({"id": user_id})
            await message.reply_text("✅ User full data deleted.")
        elif option == "b":
            if len(command_args) < 3:
                await message.reply_text("Provide amount to deduct.")
                return
            try:
                amount = int(command_args[2])
            except ValueError:
                await message.reply_text("Invalid amount.")
                return
            balance_data = await user_collection.find_one({"id": user_id})
            current_balance = balance_data.get("balance", 0)
            new_balance = max(0, current_balance - amount)
            await user_collection.update_one({"id": user_id}, {"$set": {"balance": new_balance}})
            await message.reply_text(f"💰 Deducted {amount}. New balance: {new_balance}")
        else:
            await message.reply_text("Unknown option.")
    except Exception as e:
        print(f"/kill error: {e}")
        await message.reply_text(f"Error: {e}")
