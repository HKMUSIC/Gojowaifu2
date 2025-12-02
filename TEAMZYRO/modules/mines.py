from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import random
from motor.motor_asyncio import AsyncIOMotorClient
from TEAMZYRO import app   # YOUR BOT INSTANCE


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



# -------------------- START MINES --------------------
@app.on_message(filters.command("mines"))
async def start_mines(client, message):

    user = await get_user(message.from_user.id)

    if user["lockbalance"]:
        await message.reply("❌ Your balance is locked. Use /unlockbalance first.")
        return

    # Setup game
    bombs = random.sample(range(1, 26), 5)

    await mines_games.update_one(
        {"user_id": user["id"]},
        {
            "$set": {
                "user_id": user["id"],
                "bombs": bombs,
                "opened": [],
                "multiplier": 1.0,
                "active": True
            }
        },
        upsert=True
    )

    # Build first empty grid
    keyboard = []
    for i in range(0, 25, 5):
        row = [
            InlineKeyboardButton("⬜", callback_data=f"mine_{message.from_user.id}_{j}")
            for j in range(i + 1, i + 6)
        ]
        keyboard.append(row)

    await message.reply(
        "💣 <b>Mines Game Started!</b>\nClick boxes and avoid bombs!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )



# -------------------- WHEN USER CLICKS A TILE --------------------
@app.on_callback_query(filters.regex("mine_"))
async def mine_click(client, query: CallbackQuery):

    parts = query.data.split("_")
    owner_id = int(parts[1])  # the user who started the game
    pos = int(parts[2])       # tile number

    # ❌ Prevent other users from touching someone else's game
    if query.from_user.id != owner_id:
        await query.answer("⚠ This is NOT your game!", show_alert=True)
        return

    game = await mines_games.find_one({"user_id": owner_id, "active": True})
    if not game:
        await query.answer("Game not found!", show_alert=True)
        return

    # Check Bomb
    if pos in game["bombs"]:
        await mines_games.update_one({"user_id": owner_id}, {"$set": {"active": False}})
        await query.answer("💥 BOMB! You lost!", show_alert=True)
        await query.message.edit("💥 GAME OVER! You hit a bomb.")
        return

    # Safe
    if pos not in game["opened"]:
        game["opened"].append(pos)
        multiplier = round(1 + 0.3 * len(game["opened"]), 2)

        await mines_games.update_one(
            {"user_id": owner_id},
            {"$set": {"opened": game["opened"], "multiplier": multiplier}}
        )

        await query.answer(f"Safe! Multiplier: {multiplier}x")

    # Draw NEW updated grid
    keyboard = []
    for i in range(0, 25, 5):
        row = []
        for tile in range(i + 1, i + 6):
            if tile in game["opened"]:
                emoji = "🟦"
            else:
                emoji = "⬜"

            row.append(InlineKeyboardButton(
                emoji,
                callback_data=f"mine_{owner_id}_{tile}"
            ))
        keyboard.append(row)

    await query.message.edit_reply_markup(InlineKeyboardMarkup(keyboard))



# -------------------- CASHOUT --------------------
@app.on_message(filters.command("cashout"))
async def cashout(client, message):

    user = await get_user(message.from_user.id)

    if user["lockbalance"]:
        await message.reply("❌ Your balance is locked! Use /unlockbalance first.")
        return

    game = await mines_games.find_one({"user_id": user["id"], "active": True})
    if not game:
        await message.reply("No active mines game.")
        return

    earnings = int(100 * game["multiplier"])

    await users.update_one({"id": user["id"]}, {"$inc": {"balance": earnings}})
    await mines_games.update_one({"user_id": user["id"]}, {"$set": {"active": False}})

    await message.reply(f"🎉 Cashout Successful!\nYou earned: <b>{earnings}</b> coins!")
