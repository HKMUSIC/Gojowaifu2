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

# Helper: nicely mention user with HTML (escape name safely)
def mention_html(user_id, name):
    safe_name = html.escape(name).replace('"', "&quot;")
    return f'<a href="tg://user?id={user_id}">{safe_name}</a>'

# Safe helper to get a user's first name; returns string
async def safe_get_name(chat_id, user_id):
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.user.first_name or str(user_id)
    except Exception:
        return str(user_id)

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
            "level_success": 0,      # successful words count in current level (0..2)
            "last_letter": random.choice("abcdefghijklmnopqrstuvwxyz"),
            "timeout_task": None,    # asyncio.Task
            "active": False,         # game running
            "total_words": 0,        # total correct words so far
        }

    game = games[chat_id]

    if user.id in game["players"]:
        return await message.reply_text("⚠ You already joined the lobby.", parse_mode="html")

    game["players"].append(user.id)
    await message.reply_text(f"✅ {mention_html(user.id, user.first_name)} joined the lobby.", parse_mode="html")
    await message.reply_text(f"Players in lobby: {len(game['players'])}. Use /startwordgame to begin.", parse_mode="html")

# ---------------------------
# /leave - leave lobby or game
# ---------------------------
@app.on_message(filters.command("leave"))
async def wc_leave(_, message):
    chat_id = message.chat.id
    user = message.from_user

    if chat_id not in games:
        return await message.reply_text("No active lobby or game here.", parse_mode="html")

    game = games[chat_id]
    if user.id not in game["players"]:
        return await message.reply_text("You are not in the lobby/game.", parse_mode="html")

    try:
        idx = game["players"].index(user.id)
        game["players"].pop(idx)
        if game["active"]:
            if idx < game["turn_index"]:
                game["turn_index"] -= 1
            if game["players"]:
                game["turn_index"] %= len(game["players"])
            else:
                game["turn_index"] = 0
    except ValueError:
        pass

    await message.reply_text(f"✅ {mention_html(user.id, user.first_name)} left the lobby/game.", parse_mode="html")

    if not game["players"]:
        if game.get("timeout_task"):
            try:
                game["timeout_task"].cancel()
            except:
                pass
        del games[chat_id]
        await message.reply_text("Lobby closed (no players).", parse_mode="html")

# ---------------------------
# /startwordgame - start the game
# ---------------------------
@app.on_message(filters.command("startwordgame"))
async def wc_start(_, message):
    chat_id = message.chat.id

    if chat_id not in games or len(games[chat_id]["players"]) < 2:
        return await message.reply_text("Need at least 2 players to start the game.", parse_mode="html")

    game = games[chat_id]
    if game["active"]:
        return await message.reply_text("Game already running.", parse_mode="html")

    # init values
    game["active"] = True
    game["mode"] = 3
    game["level_success"] = 0
    game["turn_index"] = 0
    game["total_words"] = 0
    game["last_letter"] = random.choice("abcdefghijklmnopqrstuvwxyz")

    first_id = game["players"][game["turn_index"]]
    first_name = await safe_get_name(chat_id, first_id)
    await message.reply_text(
        "🎮 <b>WordChain Game Started!</b>\n"
        f"➡ Minimum letters: <b>{game['mode']}</b>\n"
        f"➡ First letter: <b>{html.escape(game['last_letter'])}</b>\n"
        f"➡ First turn: {mention_html(first_id, first_name)}",
        parse_mode="html"
    )

    await send_turn_message(chat_id)

# ---------------------------
# /stopwordgame - stop and cleanup
# ---------------------------
@app.on_message(filters.command("stopwordgame"))
async def wc_stop(_, message):
    chat_id = message.chat.id
    if chat_id not in games:
        return await message.reply_text("No active game to stop.", parse_mode="html")

    game = games[chat_id]
    if game.get("timeout_task"):
        try:
            game["timeout_task"].cancel()
        except:
            pass

    del games[chat_id]
    await message.reply_text("🛑 WordChain game stopped and cleaned up.", parse_mode="html")

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

    if not game["players"]:
        if game.get("timeout_task"):
            try:
                game["timeout_task"].cancel()
            except:
                pass
        del games[chat_id]
        return

    if len(game["players"]) > 0:
        game["turn_index"] %= len(game["players"])
    else:
        game["turn_index"] = 0

    current_id = game["players"][game["turn_index"]]
    next_id = game["players"][(game["turn_index"] + 1) % len(game["players"])] if len(game["players"]) > 1 else current_id

    cur_name = await safe_get_name(chat_id, current_id)
    next_name = await safe_get_name(chat_id, next_id)

    txt = (
        f"🎯 Turn: {mention_html(current_id, cur_name)}\n"
        f"➡ Word must start with: <b>{html.escape(game['last_letter'])}</b>\n"
        f"➡ Minimum letters: <b>{game['mode']}</b>\n"
        f"⏳ You have <b>{time_for_mode(game['mode'])}</b> seconds!\n\n"
        f"👥 Players remaining: <b>{len(game['players'])}</b>\n"
        f"🔢 Total words: <b>{game['total_words']}</b>\n"
        f"🔜 Next: {mention_html(next_id, next_name)}"
    )

    await app.send_message(chat_id, txt, parse_mode="html")

    if game.get("timeout_task"):
        try:
            game["timeout_task"].cancel()
        except:
            pass

    async def _timeout_worker():
        try:
            await asyncio.sleep(time_for_mode(game["mode"]))
            if chat_id not in games:
                return
            g = games[chat_id]
            if not g["active"]:
                return
            if not g["players"]:
                return
            try:
                removed_id = g["players"].pop(g["turn_index"])
            except Exception:
                return

            removed_name = await safe_get_name(chat_id, removed_id)
            await app.send_message(chat_id,
                f"⏱ <b>Timeout!</b>\n"
                f"❌ Player removed due to timeout: {mention_html(removed_id, removed_name)}",
                parse_mode="html"
            )

            if len(g["players"]) <= 1:
                if g["players"]:
                    winner_id = g["players"][0]
                    winner_name = await safe_get_name(chat_id, winner_id)
                    await app.send_message(chat_id, f"🏆 <b>Winner:</b> {mention_html(winner_id, winner_name)}", parse_mode="html")
                if g.get("timeout_task"):
                    try:
                        g["timeout_task"].cancel()
                    except:
                        pass
                del games[chat_id]
                return

            g["turn_index"] %= len(g["players"])
            await asyncio.sleep(1)
            await send_turn_message(chat_id)
        except asyncio.CancelledError:
            return
        except Exception:
            try:
                await app.send_message(chat_id, "⚠ An internal error occurred in timeout handler.", parse_mode="html")
            except:
                pass
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

    if not game["players"]:
        return

    game["turn_index"] %= len(game["players"])
    current_player = game["players"][game["turn_index"]]
    if user.id != current_player:
        return

    word = message.text.strip().lower()

    if not word.isalpha():
        await message.reply_text("❌ Invalid format. Use plain words (letters only).", parse_mode="html")
        return

    if not word.startswith(game["last_letter"]):
        await message.reply_text(f"❌ Wrong starting letter. Word must start with: <b>{html.escape(game['last_letter'])}</b>", parse_mode="html")
        return

    if len(word) < game["mode"]:
        await message.reply_text(f"❌ Word is too short. Minimum letters required: <b>{game['mode']}</b>", parse_mode="html")
        return

    if WORDS and word not in WORDS:
        await message.reply_text("❌ Not a valid English word (according to wordlist).", parse_mode="html")
        return

    if game.get("timeout_task"):
        try:
            game["timeout_task"].cancel()
        except:
            pass

    game["total_words"] += 1
    game["level_success"] += 1
    game["last_letter"] = word[-1]

    if game["level_success"] >= 3 and game["mode"] < 10:
        game["mode"] += 1
        game["level_success"] = 0
        lvl_msg = f"🔥 Level up! Minimum letters is now <b>{game['mode']}</b>."
    else:
        lvl_msg = None

    await app.send_message(chat_id,
        f"✔ Correct! {mention_html(user.id, user.first_name)} played <b>{html.escape(word)}</b>.\n"
        + (f"{lvl_msg}" if lvl_msg else ""),
        parse_mode="html"
    )

    if game["players"]:
        game["turn_index"] = (game["turn_index"] + 1) % len(game["players"])
    else:
        game["turn_index"] = 0

    await asyncio.sleep(0.8)
    await send_turn_message(chat_id)
