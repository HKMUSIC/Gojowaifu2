from pyrogram import Client, filters
import asyncio
import random

app = Client("wordgame", api_id=24965086, api_hash="b9c764ce47c010e1a887f19fea54f648")

# Load word list
import os

FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "words.txt")

with open(FILE_PATH, "r") as f:
    WORDS = set(w.strip().lower() for w in f.readlines())

games = {}  # store game data per chat

# -------------------------------------------------------
# /join
# -------------------------------------------------------
@app.on_message(filters.command("join"))
async def join_game(_, message):
    chat_id = message.chat.id

    if chat_id not in games:
        games[chat_id] = {
            "players": [],
            "turn_index": 0,
            "mode": 3,
            "last_letter": random.choice("abcdefghijklmnopqrstuvwxyz"),
            "timeout_task": None,
            "active": False,
        }

    game = games[chat_id]

    if message.from_user.id in game["players"]:
        return await message.reply("Already joined!")

    game["players"].append(message.from_user.id)
    await message.reply(f"✔ {message.from_user.first_name} joined the game!")

# -------------------------------------------------------
# /startgame
# -------------------------------------------------------
@app.on_message(filters.command("startgame"))
async def start_game(_, message):
    chat_id = message.chat.id

    if chat_id not in games or len(games[chat_id]["players"]) < 2:
        return await message.reply("Need at least 2 players to start!")

    game = games[chat_id]
    game["active"] = True
    game["mode"] = 3
    game["turn_index"] = 0
    game["last_letter"] = random.choice("abcdefghijklmnopqrstuvwxyz")

    await message.reply(
        f"🎮 Word Game Started!\n"
        f"➡ First letter: **{game['last_letter']}**\n"
        f"➡ Minimum letters: **{game['mode']}**"
    )

    await next_turn(message)

# -------------------------------------------------------
# /stopgame
# -------------------------------------------------------
@app.on_message(filters.command("stopgame"))
async def stop_game(_, message):
    chat_id = message.chat.id

    if chat_id in games:
        if games[chat_id]["timeout_task"]:
            games[chat_id]["timeout_task"].cancel()
        del games[chat_id]

    await message.reply("🛑 Game stopped.")

# -------------------------------------------------------
# TURN SYSTEM + TIMEOUT
# -------------------------------------------------------
async def next_turn(message):
    chat_id = message.chat.id
    game = games[chat_id]

    current_player = game["players"][game["turn_index"]]

    msg = await message.reply(
        f"🎯 **Turn:** {message.chat.get_member(current_player).user.first_name}\n"
        f"➡ Word must start with: **{game['last_letter']}**\n"
        f"➡ Minimum letters: **{game['mode']}**\n"
        f"⏳ You have 15 seconds!"
    )

    # timeout kick
    async def timeout():
        await asyncio.sleep(15)
        try:
            kicked = game["players"].pop(game["turn_index"])
            await message.reply(
                f"⏱ Timeout! Player kicked from game.\n"
                f"🚫 Removed: `{kicked}`"
            )
        except:
            return

        if len(game["players"]) < 2:
            del games[chat_id]
            return await message.reply("Game ended — not enough players.")

        game["turn_index"] %= len(game["players"])
        await next_turn(message)

    # start timeout
    if game["timeout_task"]:
        game["timeout_task"].cancel()

    game["timeout_task"] = asyncio.create_task(timeout())

# -------------------------------------------------------
# PLAYER WORD INPUT
# -------------------------------------------------------
@app.on_message(filters.text & ~filters.command([]))
async def game_turn(_, message):
    chat_id = message.chat.id

    if chat_id not in games:
        return

    game = games[chat_id]
    if not game["active"]:
        return

    # must be the current player
    player = game["players"][game["turn_index"]]
    if message.from_user.id != player:
        return

    word = message.text.lower()

    # check starting letter
    if not word.startswith(game["last_letter"]):
        return await message.reply("❌ Wrong starting letter!")

    # check minimum length
    if len(word) < game["mode"]:
        return await message.reply(f"❗ Word must be at least **{game['mode']}** letters!")

    # dictionary check
    if word not in WORDS:
        return await message.reply("❗ Not a valid English word!")

    # correct → update last letter
    game["last_letter"] = word[-1]

    # increase mode up to 10
    if game["mode"] < 10:
        game["mode"] += 1

    # stop timeout
    if game["timeout_task"]:
        game["timeout_task"].cancel()

    await message.reply(
        f"✔ Correct!\n"
        f"➡ Next starting letter: **{game['last_letter']}**\n"
        f"➡ Next minimum letters: **{game['mode']}**"
    )

    # next player
    game["turn_index"] = (game["turn_index"] + 1) % len(game["players"])

    await next_turn(message)

# -------------------------------------------------------
print("Bot Running...")
app.run()
