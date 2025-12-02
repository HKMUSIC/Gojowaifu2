from TEAMZYRO import ZYRO as app
from pyrogram import filters
import asyncio
import random
import os

FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "words.txt")
with open(FILE_PATH, "r") as f:
    WORDS = set(w.strip().lower() for w in f.readlines())

games = {}

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
            "repeat": 0,
            "last_letter": random.choice("abcdefghijklmnopqrstuvwxyz"),
            "timeout_task": None,
            "active": False,
            "total_words": 0
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
    game["repeat"] = 0
    game["turn_index"] = 0
    game["total_words"] = 0
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
# NEXT TURN MESSAGE
# -------------------------------------------------------
async def next_turn(message):
    chat_id = message.chat.id
    game = games[chat_id]

    current_player = game["players"][game["turn_index"]]
    user = await app.get_chat_member(chat_id, current_player)
    mention = user.user.mention

    # TIME SETTINGS BY MODE
    time_map = {
        3: 40, 
        4: 35,
        5: 30,
        6: 30,
        7: 25,
        8: 25,
        9: 20,
        10: 20
    }

    turn_time = time_map.get(game["mode"], 20)

    msg = await message.reply(
        f"Bot Turn: {mention} ⭐\n"
        f"(Next: {mention})\n"
        f"Your word must start with **{game['last_letter'].upper()}** "
        f"and include at least **{game['mode']} letters**.\n"
        f"You have {turn_time}s to answer.\n"
        f"Players remaining: {len(game['players'])}/{len(game['players'])}\n"
        f"Total words: {game['total_words']}"
    )

    async def timeout():
        await asyncio.sleep(turn_time)
        kicked = game["players"].pop(game["turn_index"])
        await message.reply(f"⏱ Timeout! Player removed: `{kicked}`")

        if len(game["players"]) < 2:
            del games[chat_id]
            return await message.reply("Game ended — not enough players.")

        game["turn_index"] %= len(game["players"])
        await next_turn(message)

    if game["timeout_task"]:
        game["timeout_task"].cancel()

    game["timeout_task"] = asyncio.create_task(timeout())

# -------------------------------------------------------
# WORD INPUT HANDLING
# -------------------------------------------------------
@app.on_message(filters.text & ~filters.command([]))
async def game_turn(_, message):
    chat_id = message.chat.id

    if chat_id not in games:
        return

    game = games[chat_id]
    if not game["active"]:
        return

    player = game["players"][game["turn_index"]]
    if message.from_user.id != player:
        return

    word = message.text.lower()

    # Wrong starting letter (with mention)
    if not word.startswith(game["last_letter"]):
        return await message.reply(f"{message.from_user.mention} ❌ Wrong starting letter!")

    # Word too short (with mention)
    if len(word) < game["mode"]:
        return await message.reply(
            f"{message.from_user.mention} ❗ Word must be at least **{game['mode']}** letters!"
        )

    # Invalid English word (with mention)
    if word not in WORDS:
        return await message.reply(
            f"{message.from_user.mention} ❗ Not a valid English word!"
        )

    # ACCEPTED WORD
    game["last_letter"] = word[-1]
    game["total_words"] += 1

    # Send "word is accepted"
    await message.reply(f"{word} is accepted.")

    # REPEAT LEVEL 3 TIMES BEFORE INCREMENT
    if game["mode"] < 10:
        game["repeat"] += 1
        if game["repeat"] == 3:
            game["repeat"] = 0
            game["mode"] += 1

    # Level 10 stays forever
    if game["mode"] == 10:
        game["repeat"] = 0

    if game["timeout_task"]:
        game["timeout_task"].cancel()

    game["turn_index"] = (game["turn_index"] + 1) % len(game["players"])
    await next_turn(message)
