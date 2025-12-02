from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
import random
from TEAMZYRO import app


# -------------------- MONGO SETUP --------------------
mongo = AsyncIOMotorClient("mongodb+srv://Gojowaifu2:Gojowaifu2@cluster0.uvox90s.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = mongo["GAME_DB"]

users = db.users
mines_games = db.mines_games


# -------------------- USER FETCH --------------------
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

    parts = message.text.split()

    if len(parts) == 1:
        return await message.reply("Usage:\n`/mines 100` to start with 100 coins.")

    # bet amount
    try:
        bet = int(parts[1])
        if bet <= 0:
            return await message.reply("Amount must be positive.")
    except:
        return await message.reply("Invalid amount.")

    user = await get_user(message.from_user.id)

    # balance lock check
    if user["lockbalance"]:
        return await message.reply("❌ Your balance is locked! Use /unlockbalance")

    # balance check
    if user["balance"] < bet:
        return await message.reply("❌ Not enough balance!")

    # deduct balance
    await users.update_one({"id": user["id"]}, {"$inc": {"balance": -bet}})

    # reload user (important!)
    user = await get_user(user["id"])

    # create bombs
    bombs = random.sample(range(1, 26), 5)

    # save game session
    await mines_games.update_one(
        {"user_id": user["id"]},
        {"$set": {
            "user_id": user["id"],
            "bombs": bombs,
            "opened": [],
            "multiplier": 1.0,
            "active": True,
            "bet": bet
        }},
        upsert=True
    )

    keyboard = build_grid(user["id"], [], True)

    await message.reply(
        f"💣 <b>Mines Started!</b>\n"
        f"Bet: <b>{bet}</b>\nMultiplier: <b>1.0x</b>\nProfit: <b>0</b>",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# -------------------- WHEN USER CLICKS A TILE --------------------
@app.on_callback_query(filters.regex("^mine_"))
async def mine_click(client, query: CallbackQuery):

    try:
        parts = query.data.split("_")
        owner_id = int(parts[1])
        pos = int(parts[2])
    except:
        return await query.answer("Error!", show_alert=True)

    # only owner can click
    if query.from_user.id != owner_id:
        return await query.answer("⚠ This is not your game!", show_alert=True)

    # load game
    game = await mines_games.find_one({"user_id": owner_id, "active": True})
    if not game:
        return await query.answer("Game expired!", show_alert=True)

    bet = game["bet"]

    # bomb clicked
    if pos in game["bombs"]:
        await mines_games.update_one({"user_id": owner_id}, {"$set": {"active": False}})
        keyboard = reveal_bombs(owner_id, game["bombs"], game["opened"])
        return await query.message.edit(
            "💥 <b>BOOM! You hit a bomb.</b>\nGame Over!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # safe tile
    if pos not in game["opened"]:
        game["opened"].append(pos)

        multiplier = round(1.0 + 0.30 * len(game["opened"]), 2)

        await mines_games.update_one(
            {"user_id": owner_id},
            {"$set": {"opened": game["opened"], "multiplier": multiplier}}
        )

        await query.answer(f"Safe! {multiplier}x")

    profit = int((bet * game["multiplier"]) - bet)

    keyboard = build_grid(owner_id, game["opened"], True)

    await query.message.edit(
        f"💣 <b>Mines Game</b>\n"
        f"Bet: <b>{bet}</b>\n"
        f"Multiplier: <b>{game['multiplier']}x</b>\n"
        f"Profit: <b>{profit}</b>",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# -------------------- CASHOUT BUTTON --------------------
@app.on_callback_query(filters.regex("^cashout_"))
async def cashout_button(client, query: CallbackQuery):

    uid = int(query.data.split("_")[1])

    if query.from_user.id != uid:
        return await query.answer("⚠ Not your game!", show_alert=True)

    # load user
    user = await get_user(uid)

    if user["lockbalance"]:
        return await query.answer("🔒 Your balance is locked.", show_alert=True)

    # load game
    game = await mines_games.find_one({"user_id": uid, "active": True})
    if not game:
        return await query.answer("Game already finished!")

    bet = game["bet"]
    multiplier = game["multiplier"]

    earnings = int(bet * multiplier)

    # add money
    await users.update_one({"id": uid}, {"$inc": {"balance": earnings}})

    # end game
    await mines_games.update_one({"user_id": uid}, {"$set": {"active": False}})

    await query.message.edit(
        f"🟩 <b>CASHOUT SUCCESS</b>\n"
        f"Bet: <b>{bet}</b>\nMultiplier: <b>{multiplier}x</b>\n"
        f"Won: <b>{earnings}</b>"
    )

    await query.answer("Cashed Out!")


# -------------------- GRID MAKER --------------------
def build_grid(uid, opened, include_cashout):

    keyboard = []

    for i in range(0, 25, 5):
        row = []
        for tile in range(i + 1, i + 6):

            emoji = "🟦" if tile in opened else "⬜"

            row.append(
                InlineKeyboardButton(
                    emoji,
                    callback_data=f"mine_{uid}_{tile}"
                )
            )

        keyboard.append(row)

    if include_cashout:
        keyboard.append([InlineKeyboardButton("🟩 CASHOUT", callback_data=f"cashout_{uid}")])

    return keyboard


# -------------------- REVEAL ALL BOMBS --------------------
def reveal_bombs(uid, bombs, opened):

    keyboard = []

    for i in range(0, 25, 5):
        row = []
        for tile in range(i + 1, i + 6):

            if tile in bombs:
                emoji = "💣"
            elif tile in opened:
                emoji = "🟦"
            else:
                emoji = "⬜"

            row.append(
                InlineKeyboardButton(
                    emoji,
                    callback_data="disabled"
                )
            )

        keyboard.append(row)

    return keyboard
