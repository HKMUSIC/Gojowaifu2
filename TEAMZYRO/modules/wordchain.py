# TEAMZYRO/modules/wordchain.py
from TEAMZYRO import ZYRO as app
from pyrogram import filters
import asyncio
import random
import os
import html

# ---------------------------
# Load word list (path-safe)
# ---------------------------
BASE_DIR = os.path.dirname(__file__)  # TEAMZYRO/modules
WORD_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "words.txt"))

if not os.path.exists(WORD_FILE):
    # Failsafe: create empty set if missing (bot won't crash)
    WORDS = set()
else:
    with open(WORD_FILE, "r", encoding="utf-8") as f:
        WORDS = set(w.strip().lower() for w in f if w.strip())

# ---------------------------
# Time per minimum-letter mode
# ---------------------------
TIME_PER_MODE = {
    3: 40,
    4: 35,
    5: 30,
    6: 30,
    7: 25,
    8: 25,
    9: 20,
    10: 20,
}

# ---------------------------
# Game storage
# chat_id -> game dict
# ---------------------------
games = {}

# Helper: nicely mention user with HTML
def mention_html(user_id, name):
    safe = html.escape(name)
    return f"<a href='tg://user?id={user_id}'>{safe}</a>"

# ---------------------------
# /join - join lobby
# ---------------------------
@app.on_message(filters.command("join"))
async def wc_join(_, message):
    chat_id = message.chat.id
    user = message.from_user

    if chat_id not in games:
        games[chat_id] = {
            "players": [],           # list of user ids
            "turn_index": 0,         # index into players
            "mode": 3,               # current minimum letters
            "level_success": 0,      # number of successful words this level (0..2) -> on 3 -> level up
            "last_letter": random.choice("abcdefghijklmnopqrstuvwxyz"),
            "timeout_task": None,    # asyncio.Task
            "active": False,         # game running
            "total_words": 0,        # total correct words so far
        }

    game = games[chat_id]

    if user.id in game["players"]:
        return await message.reply_text("⚠ You already joined the lobby.")

    game["players"].append(user.id)
    await message.reply_text(f"✅ {mention_html(user.id, user.first_name)} joined the lobby.", parse_mode="HTML")

    # If you want to auto-start on 2 players, comment next block.
    # We'll keep manual start via /startwordgame
    # But you can notify how many players joined:
    await message.reply_text(f"Players in lobby: {len(game['players'])}. Use /startwordgame to begin.", parse_mode="HTML")

# ---------------------------
# /leave - leave lobby or game
# ---------------------------
@app.on_message(filters.command("leave"))
async def wc_leave(_, message):
    chat_id = message.chat.id
    user = message.from_user

    if chat_id not in games:
        return await message.reply_text("No active lobby or game here.")

    game = games[chat_id]
    if user.id not in game["players"]:
        return await message.reply_text("You are not in the lobby/game.")

    # If game running and it's this player's turn and there's a timeout task, cancel? We'll remove and continue.
    try:
        idx = game["players"].index(user.id)
        game["players"].pop(idx)
        # adjust turn_index if needed
        if game["active"]:
            if idx < game["turn_index"]:
                game["turn_index"] -= 1
            game["turn_index"] %= max(1, len(game["players"])) if game["players"] else 0
    except ValueError:
        pass

    await message.reply_text(f"✅ {mention_html(user.id, user.first_name)} left the lobby/game.", parse_mode="HTML")

    if not game["players"]:
        # cleanup
        if game.get("timeout_task"):
            try:
                game["timeout_task"].cancel()
            except:
                pass
        del games[chat_id]
        await message.reply_text("Lobby closed (no players).")

# ---------------------------
# /startwordgame - start the game
# ---------------------------
@app.on_message(filters.command("startwordgame"))
async def wc_start(_, message):
    chat_id = message.chat.id

    if chat_id not in games or len(games[chat_id]["players"]) < 2:
        return await message.reply_text("Need at least 2 players to start the game.")

    game = games[chat_id]
    if game["active"]:
        return await message.reply_text("Game already running.")

    # init values
    game["active"] = True
    game["mode"] = 3
    game["level_success"] = 0
    game["turn_index"] = 0
    game["total_words"] = 0
    game["last_letter"] = random.choice("abcdefghijklmnopqrstuvwxyz")

    # announce start (no raw user id)
    first_id = game["players"][game["turn_index"]]
    first_name = (await app.get_chat_member(chat_id, first_id)).user.first_name
    await message.reply_text(
        "🎮 <b>WordChain Game Started!</b>\n"
        f"➡ Minimum letters: <b>{game['mode']}</b>\n"
        f"➡ First letter: <b>{html.escape(game['last_letter'])}</b>\n"
        f"➡ First turn: {mention_html(first_id, first_name)}",
        parse_mode="HTML"
    )

    # start first turn
    await send_turn_message(chat_id)

# ---------------------------
# /stopwordgame - stop and cleanup
# ---------------------------
@app.on_message(filters.command("stopwordgame"))
async def wc_stop(_, message):
    chat_id = message.chat.id
    if chat_id not in games:
        return await message.reply_text("No active game to stop.")

    game = games[chat_id]
    if game.get("timeout_task"):
        try:
            game["timeout_task"].cancel()
        except:
            pass

    del games[chat_id]
    await message.reply_text("🛑 WordChain game stopped and cleaned up.")

# ---------------------------
# Helper: compute timeout seconds for current mode
# ---------------------------
def time_for_mode(mode: int) -> int:
    return TIME_PER_MODE.get(mode, 20)

# ---------------------------
# Send the turn message (with stats) and start timeout
# ---------------------------
async def send_turn_message(chat_id: int):
    if chat_id not in games:
        return
    game = games[chat_id]
    if not game["active"]:
        return

    # ensure there are players
    if not game["players"]:
        # cleanup
        del games[chat_id]
        return

    # clamp turn_index
    game["turn_index"] %= len(game["players"])

    current_id = game["players"][game["turn_index"]]
    next_id = game["players"][(game["turn_index"] + 1) % len(game["players"])] if len(game["players"]) > 1 else current_id

    # fetch user names
    try:
        cur_member = await app.get_chat_member(chat_id, current_id)
        cur_name = cur_member.user.first_name
    except Exception:
        cur_name = str(current_id)

    try:
        next_member = await app.get_chat_member(chat_id, next_id)
        next_name = next_member.user.first_name
    except Exception:
        next_name = str(next_id)

    # build message
    txt = (
        f"🎯 Turn: {mention_html(current_id, cur_name)}\n"
        f"➡ Word must start with: <b>{html.escape(game['last_letter'])}</b>\n"
        f"➡ Minimum letters: <b>{game['mode']}</b>\n"
        f"⏳ You have <b>{time_for_mode(game['mode'])}</b> seconds!\n\n"
        f"👥 Players remaining: <b>{len(game['players'])}</b>\n"
        f"🔢 Total words: <b>{game['total_words']}</b>\n"
        f"🔜 Next: {mention_html(next_id, next_name)}"
    )

    # send message to chat
    await app.send_message(chat_id, txt, parse_mode="HTML")

    # start timeout for this turn
    # cancel previous
    if game.get("timeout_task"):
        try:
            game["timeout_task"].cancel()
        except:
            pass

    # create new timeout task
    async def _timeout_worker():
        try:
            await asyncio.sleep(time_for_mode(game["mode"]))
            # If still active and player didn't answer in time -> eliminate
            # Player removed
            if chat_id not in games:
                return
            g = games[chat_id]
            if not g["active"]:
                return
            # ensure same turn_index valid
            if not g["players"]:
                return
            try:
                removed_id = g["players"].pop(g["turn_index"])
            except Exception:
                return
            # announce elimination
            await app.send_message(chat_id,
                f"⏱ <b>Timeout!</b>\n"
                f"❌ Player removed due to timeout: {mention_html(removed_id, (await app.get_chat_member(chat_id, removed_id)).user.first_name)}",
                parse_mode="HTML"
            )
            # If <=1 player left: declare winner or stop
            if len(g["players"]) <= 1:
                if g["players"]:
                    winner_id = g["players"][0]
                    winner_name = (await app.get_chat_member(chat_id, winner_id)).user.first_name
                    await app.send_message(chat_id, f"🏆 <b>Winner:</b> {mention_html(winner_id, winner_name)}", parse_mode="HTML")
                del games[chat_id]
                return
            # ensure turn_index within bounds
            g["turn_index"] %= len(g["players"])
            # continue next turn (same function)
            await asyncio.sleep(1)
            await send_turn_message(chat_id)
        except asyncio.CancelledError:
            return

    task = asyncio.create_task(_timeout_worker())
    game["timeout_task"] = task

# ---------------------------
# Message handler for answers (only current player allowed)
# ---------------------------
@app.on_message(filters.text & ~filters.command([]))
async def wc_handle_answer(_, message):
    chat_id = message.chat.id
    user = message.from_user

    if chat_id not in games:
        return

    game = games[chat_id]
    if not game["active"]:
        return

    # current player must match
    # ensure index in range
    game["turn_index"] %= max(1, len(game["players"]))
    current_player = game["players"][game["turn_index"]]
    if user.id != current_player:
        # ignore other players' messages
        return

    word = message.text.strip().lower()

    # quick validation: alphabets only (allow apostrophe? currently only letters)
    if not word.isalpha():
        await message.reply_text(f"❌ Invalid format. Use plain words (letters only).", parse_mode="HTML")
        return

    # starting letter check
    if not word.startswith(game["last_letter"]):
        await message.reply_text(
            f"❌ Wrong starting letter. Word must start with: <b>{html.escape(game['last_letter'])}</b>",
            parse_mode="HTML"
        )
        return

    # minimum length check (mode is minimum)
    if len(word) < game["mode"]:
        await message.reply_text(
            f"❌ Word is too short. Minimum letters required: <b>{game['mode']}</b>",
            parse_mode="HTML"
        )
        return

    # dictionary check (if WORDS empty, allow everything)
    if WORDS and word not in WORDS:
        await message.reply_text("❌ Not a valid English word (according to wordlist).", parse_mode="HTML")
        return

    # Passed -> correct answer
    # Cancel timeout for this turn
    if game.get("timeout_task"):
        try:
            game["timeout_task"].cancel()
        except:
            pass

    # update stats
    game["total_words"] += 1
    game["level_success"] += 1
    game["last_letter"] = word[-1]

    # If this level achieved 3 successful words -> level up
    if game["level_success"] >= 3 and game["mode"] < 10:
        game["mode"] += 1
        game["level_success"] = 0
        lvl_msg = f"🔥 Level up! Minimum letters is now <b>{game['mode']}</b>."
    else:
        lvl_msg = None

    # Notify correct (no forced mention except the reply by player itself)
    await app.send_message(chat_id,
        f"✔ Correct! {mention_html(user.id, user.first_name)} played <b>{html.escape(word)}</b>.\n"
        + (f"{lvl_msg}" if lvl_msg else ""),
        parse_mode="HTML"
    )

    # advance turn (same round)
    game["turn_index"] = (game["turn_index"] + 1) % len(game["players"])

    # small delay then send next turn message
    await asyncio.sleep(0.8)
    await send_turn_message(chat_id)
