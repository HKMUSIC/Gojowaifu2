import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message

games = {}  # Stores active games


class WordGame:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.players = []
        self.used_words = set()
        self.current_player = 0
        self.game_running = False
        self.letter_limit = 3
        self.turns = 0
        self.timeout = 20

        with open("downloads/words.txt", "r") as f:
            self.words = {w.strip().lower() for w in f.readlines() if w.strip()}

    def next_player(self):
        self.current_player = (self.current_player + 1) % len(self.players)
        return self.players[self.current_player]

    def increase_limit(self):
        if self.letter_limit < 10:
            self.letter_limit += 1


# -------------------------------
# /join command
# -------------------------------
@Client.on_message(filters.command("join"))
async def join_wordgame(_, m: Message):
    chat = m.chat.id
    user = m.from_user.id

    if chat not in games:
        games[chat] = WordGame(chat)

    game = games[chat]

    if game.game_running:
        return await m.reply("⚠ Game already started!")

    if user in game.players:
        return await m.reply("You already joined!")

    game.players.append(user)
    await m.reply(f"➕ **{m.from_user.first_name} joined the game!**")


# -------------------------------
# /startgame command
# -------------------------------
@Client.on_message(filters.command("startgame"))
async def start_wordgame(_, m: Message):
    chat = m.chat.id
    if chat not in games:
        return await m.reply("No game lobby! Use /join first.")

    game = games[chat]

    if len(game.players) < 2:
        return await m.reply("❗ Need at least 2 players to start.")

    game.game_running = True
    first = game.players[0]

    await m.reply(f"🎮 **WordChain Game Started!**\n"
                  f"▶ First turn: { (await _.get_users(first)).first_name }\n"
                  f"Letter requirement: **{game.letter_limit} letters**")

    asyncio.create_task(run_turn(_, m))


# -------------------------------
# Turn System
# -------------------------------
async def run_turn(app: Client, m: Message):
    chat = m.chat.id
    game = games[chat]

    while game.game_running and len(game.players) > 1:
        player_id = game.players[game.current_player]
        user = await app.get_users(player_id)

        await m.reply(
            f"⏳ **{user.first_name}'s turn!**\n"
            f"Word must be ≥ **{game.letter_limit} letters**"
        )

        try:
            reply = await app.listen(chat, timeout=game.timeout)

            if reply.from_user.id != player_id:
                continue  # Ignore other messages

            word = reply.text.lower().strip()

            # Validate word
            if len(word) < game.letter_limit:
                await m.reply(f"❌ Word too short! Eliminated: {user.first_name}")
                game.players.remove(player_id)
                continue

            if word not in game.words:
                await m.reply(f"❌ Invalid word! Eliminated: {user.first_name}")
                game.players.remove(player_id)
                continue

            if word in game.used_words:
                await m.reply(f"❌ Word already used! Eliminated: {user.first_name}")
                game.players.remove(player_id)
                continue

            game.used_words.add(word)
            game.turns += 1

            # Increase limit every 5 turns
            if game.turns % 5 == 0:
                game.increase_limit()
                await m.reply(f"🔥 Letter limit increased to **{game.letter_limit}**!")

            # Next player
            game.next_player()

        except asyncio.TimeoutError:
            await m.reply(f"⌛ Timeout! Eliminated: {user.first_name}")
            game.players.remove(player_id)
            if len(game.players) <= 1:
                break

    # Winner
    if len(game.players) == 1:
        winner_id = game.players[0]
        winner = await app.get_users(winner_id)

        await m.reply(f"👑 Winner: **{winner.first_name}** 🎉")
    else:
        await m.reply("Game ended.")

    del games[chat]
