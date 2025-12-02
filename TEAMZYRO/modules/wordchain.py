from TEAMZYRO import app
from pyrogram import filters
import asyncio
import random

# ==============================
# WORD LIST LOAD
# ==============================
import aiohttp

WORD_URL = "https://raw.githubusercontent.com/dwyl/english-words/master/words.txt"
WORDS = []

async def load_words():
    global WORDS
    async with aiohttp.ClientSession() as session:
        async with session.get(WORD_URL) as resp:
            text = await resp.text()
            WORDS = text.splitlines()

app.loop.create_task(load_words())  # load words on startup

# ==============================
# GAME STATE
# ==============================

games = {}  # chat_id : { players, turn_index, mode, last_letter, timeout_task }


# ==============================
# /join
# ==============================
@app.on_message(filters.command("join"))
async def join_game(_, message):
    chat_id = message.chat.id
    user = message.from_user

    if chat_id not in games:
        games[chat_id] = {
            "players": [],
            "turn_index": 0,
            "mode": 3,              # starting with 3-letter words
            "last_letter": None,
            "timeout_task": None
        }

    game = games[chat_id]

    # Add player
    if user.id in game["players"]:
        return await message.reply(f"❗ {user.mention} you are already in the game.")

    game["players"].append(user.id)
    await message.reply(f"✅ {user.mention} joined the WordChain game!\nPlayers: {len(game['players'])}")

    # Start game when 2+ players
    if len(game["players"]) == 2:
        await start_round(message)


# ==============================
# START ROUND
# ==============================
async def start_round(message):
    chat_id = message.chat.id
    game = games[chat_id]

    player_id = game["players"][game["turn_index"]]
    game["last_letter"] = random.choice("abcdefghijklmnopqrstuvwxyz")

    await message.reply(
        f"🎮 **WordChain Game Started!**\n"
        f"👉 Mode: `{game['mode']}` letters\n"
        f"👉 Starting letter: `{game['last_letter']}`\n"
        f"👉 Player turn: [{player_id}](tg://user?id={player_id})"
    )

    await start_timeout(message)


# ==============================
# TIMEOUT HANDLER
# ==============================
async def start_timeout(message):
    chat_id = message.chat.id
    game = games[chat_id]

    if game["timeout_task"]:
        game["timeout_task"].cancel()

    async def kick_player():
        await asyncio.sleep(15)  # 15 sec timeout
        player = game["players"][game["turn_index"]]
        game["players"].remove(player)

        await message.reply(
            f"⏳ Timeout!\n"
            f"❌ Player kicked: [{player}](tg://user?id={player})"
        )

        if len(game["players"]) < 2:
            del games[chat_id]
            return await message.reply("🏁 Game ended. Not enough players.")

        await next_turn(message)

    game["timeout_task"] = app.loop.create_task(kick_player())


# ==============================
# MESSAGE HANDLER (TURN SYSTEM)
# ==============================
@app.on_message(filters.text & ~filters.command([]))
async def game_turn(_, message):
    chat_id = message.chat.id
    if chat_id not in games:
        return

    game = games[chat_id]
    try:
        player = game["players"][game["turn_index"]]
    except:
        return

    if message.from_user.id != player:
        return

    word = message.text.lower()

    # Check rules
    if not word.startswith(game["last_letter"]):
        return await message.reply("❌ Wrong starting letter.")

    if len(word) != game["mode"]:
        return await message.reply(f"❗ Word must be exactly `{game['mode']}` letters.")

    if word not in WORDS:
        return await message.reply("❗ Not a valid English word.")

    # Correct word
    game["last_letter"] = word[-1]  # next player must use last letter

    # Increase mode until 10
    if game["mode"] < 10:
        game["mode"] += 1

    # Cancel timeout
    if game["timeout_task"]:
        game["timeout_task"].cancel()

    await message.reply(
        f"✔ Correct!\nNext mode: `{game['mode']}` letters\nNext letter: `{game['last_letter']}`"
    )

    await next_turn(message)


# ==============================
# NEXT TURN
# ==============================
async def next_turn(message):
    chat_id = message.chat.id
    game = games[chat_id]

    game["turn_index"] = (game["turn_index"] + 1) % len(game["players"])
    player = game["players"][game["turn_index"]]

    await message.reply(
        f"👉 Next turn: [{player}](tg://user?id={player})\n"
        f"🔤 Letter: `{game['last_letter']}`\n"
        f"📏 Mode: `{game['mode']}` letters"
    )

    await start_timeout(message)
