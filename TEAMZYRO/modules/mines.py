from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import random
from TEAMZYRO import app   # or bot / ZYRO etc.
from motor.motor_asyncio import AsyncIOMotorClient

mongo = AsyncIOMotorClient("mongodb+srv://Gojowaifu2:Gojowaifu2@cluster0.uvox90s.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = mongo["GAME_DB"]

users = db.users
mines_games = db.mines_games

async def get_user(user_id):
    user = await users.find_one({"id": user_id})
    if not user:
        user = {
            "id": user_id,
            "balance": 0,
            "lockbalance": False
        }
        await users.insert_one(user)
    return user


@app.on_message(filters.command("mines"))
async def start_mines(client, message):

    user = await get_user(message.from_user.id)

    # Balance must not be locked
    if user["lockbalance"]:
        await message.reply("❌ Your balance is locked. Use /unlockbalance first.")
        return

    # Mines Game Setup
    bombs = random.sample(range(1, 26), 5)  # 5 bombs
    await mines_games.update_one(
        {"user_id": user["id"]},
        {
            "$set": {
                "bombs": bombs,
                "opened": [],
                "multiplier": 0.3,
                "active": True
            }
        },
        upsert=True
    )

    # Build Grid
    keyboard = []
    for i in range(0, 25, 5):
        row = [
            InlineKeyboardButton("⬜", callback_data=f"mine_{j}")
            for j in range(i + 1, i + 6)
        ]
        keyboard.append(row)

    await message.reply(
        "💣 <b>Mines Game Started!</b>\nClick boxes and avoid bombs!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@Client.on_callback_query(filters.regex("mine_"))
async def mine_click(client, query: CallbackQuery):

    cid = query.from_user.id
    pos = int(query.data.split("_")[1])

    game = await mines_games.find_one({"user_id": cid, "active": True})
    if not game:
        await query.answer("No active game!", show_alert=True)
        return

    # Check Bomb
    if pos in game["bombs"]:
        await mines_games.update_one({"user_id": cid}, {"$set": {"active": False}})
        await query.answer("💥 BOMB! You lost!", show_alert=True)
        await query.message.edit("💥 GAME OVER! You hit a bomb.")
        return

    # Safe box
    if pos not in game["opened"]:
        game["opened"].append(pos)
        new_multiplier = round(0.3 * len(game["opened"]), 2)
        await mines_games.update_one(
            {"user_id": cid},
            {"$set": {"opened": game["opened"], "multiplier": new_multiplier}}
        )

        await query.answer(f"Safe! Multiplier: {new_multiplier}x")

    # Update UI
    keyboard = []
    for i in range(1, 26):
        emoji = "🟦" if i in game["opened"] else "⬜"
        # build grid row wise
        # reused on update
        pass


@Client.on_message(filters.command("cashout"))
async def cashout(client, message):

    user = await get_user(message.from_user.id)

    # 🔒 Balance Locked → popup only
    if user["lockbalance"]:
        await message.reply_text(
            "❌ Your balance is locked!\nUse /unlockbalance before cashing out."
        )
        return

    game = await mines_games.find_one({"user_id": user["id"], "active": True})
    if not game:
        await message.reply("No active mines game found.")
        return

    earnings = int(100 * game["multiplier"])

    await users.update_one(
        {"id": user["id"]},
        {"$inc": {"balance": earnings}}
    )

    await mines_games.update_one({"user_id": user["id"]}, {"$set": {"active": False}})

    await message.reply(f"🎉 Cashout Successful!\nYou earned: {earnings} coins")
