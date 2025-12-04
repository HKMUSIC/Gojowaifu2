# TEAMZYRO/modules/uno.py
# UNO game module with sticker cards + PM notifications + inline UI
import random
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pyrogram import filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
)
from TEAMZYRO import app  # your bot client
# If you want to persist notify list or sticker_map to DB, I can add that later.

# ---------------- CONFIG ----------------
HAND_SIZE = 7
TURN_TIMEOUT = 90   # seconds before auto-skip/draw
USE_STICKERS = True  # set True if you will load sticker pack
DEFAULT_STICKER_SET = "unocards"  # the set name from your link
# ----------------------------------------

# Colors & values used in deck generation
COLORS = ["R", "G", "B", "Y"]  # R=Red, G=Green, B=Blue, Y=Yellow
VALUE_ORDER = ["0","1","2","3","4","5","6","7","8","9","SKIP","REV","+2"]
WILD_TYPES = ["WILD", "W4"]  # Wild and Wild+4

# maps like "R_2" -> sticker file_id (populated by /load_unostickers)
STICKER_MAP: Dict[str, str] = {}

# stores chat_id -> game state
GAMES: Dict[int, Dict[str, Any]] = {}

# users who want PM notify for new games (global)
NOTIFY_USERS = set()

# ---------------- util: deck, display ----------------
def make_deck() -> List[str]:
    deck: List[str] = []
    for c in COLORS:
        deck.append(f"{c}_0")
        for v in VALUE_ORDER[1:]:
            deck.append(f"{c}_{v}")
            deck.append(f"{c}_{v}")
    for w in WILD_TYPES:
        deck.extend([w] * 4)
    random.shuffle(deck)
    return deck

def code_to_label(card_code: str) -> str:
    # nice human text used for inline button labels (fallback)
    if card_code in ("WILD", "W4"):
        return "🎨 Wild" if card_code == "WILD" else "🔮 Wild+4"
    color, val = card_code.split("_")
    color_name = {"R":"🔴","G":"🟢","B":"🔵","Y":"🟡"}.get(color, color)
    if val == "SKIP":
        return f"{color_name} ⏭"
    if val == "REV":
        return f"{color_name} 🔁"
    if val == "+2":
        return f"{color_name} +2"
    return f"{color_name} {val}"

# ---------------- sticker loader helper ----------------
async def load_uno_stickers(set_name: str = DEFAULT_STICKER_SET) -> Tuple[int, str]:
    """
    Load stickers from the given sticker set name and map to card codes.
    Sticker names in many packs include the code; if not, you must map manually.
    This function attempts to map common naming patterns automatically:
      - sticker.emojis / sticker.set_name or sticker.file_unique_id used as fallbacks.
    Returns (count_mapped, message)
    """
    try:
        sset = await app.get_sticker_set(set_name)
    except Exception as e:
        return 0, f"Failed to fetch sticker set: {e}"

    mapped = 0
    # many sticker packs name stickers like "R_2" or "R2" or "red_2". We try multiple heuristics.
    for s in sset.stickers:
        key = None
        stname = ""
        # try sticker set sticker set name property (rare)
        try:
            stname = s.file_unique_id  # fallback unique id if no name
        except:
            stname = ""
        # best: check s.set_name or s.emoji? not always available.
        # If the sticker has associated emoji text that matches digits/colors, use that.
        # Try to guess by emoji label: not reliable. So allow manual mapping after load.
        # For now, map by sticker index pattern to common deck order if length matches.
        # We'll store sample mapping: "sticker_{index}" -> file_id so admin can later map.
        STICKER_MAP[f"STICKER_{len(STICKER_MAP)+1}"] = s.file_id
        mapped += 1

    return mapped, f"Loaded {mapped} stickers (temporary keys STICKER_#). You may need to manually map STICKER_## to actual card codes."

# admin helper command to view STICKER_MAP keys
def sticker_keys_preview() -> str:
    lines = []
    for k in list(STICKER_MAP.keys())[:50]:
        lines.append(k)
    return "\n".join(lines) or "No stickers loaded."

# ---------------- lobby & commands ----------------
@app.on_message(filters.command("new") & ~filters.private)
async def cmd_new(_, message: Message):
    chat_id = message.chat.id
    if chat_id in GAMES and GAMES[chat_id].get("active"):
        return await message.reply("A UNO game is already running here. Use /join to enter.")

    deck = make_deck()
    GAMES[chat_id] = {
        "players": [],
        "deck": deck,
        "discard": [],
        "hands": {},
        "turn_index": 0,
        "direction": 1,
        "active": False,
        "current_color": None,
        "timeout_task": None
    }
    # notify PM subscribers
    for uid in list(NOTIFY_USERS):
        try:
            await app.send_message(uid, f"New UNO lobby created in group: {message.chat.title} (tap to open).")
        except:
            # ignore failures (user blocked bot etc)
            pass

    await message.reply("✅ New UNO lobby created. Use /joinuno to join. When >=2 players are ready, use /start to begin.")

@app.on_message(filters.command("joinuno") & ~filters.private)
async def cmd_join(_, message: Message):
    chat_id = message.chat.id
    if chat_id not in GAMES:
        return await message.reply("No active UNO lobby. Use /new to create one.")
    g = GAMES[chat_id]
    if g.get("active"):
        return await message.reply("Game already started; you can't join now.")
    uid = message.from_user.id
    if uid in g["players"]:
        return await message.reply("You already joined.")
    g["players"].append(uid)
    await message.reply(f"✔ {message.from_user.mention} joined UNO. Players: {len(g['players'])}")

@app.on_message(filters.command("leave") & ~filters.private)
async def cmd_leave(_, message: Message):
    chat_id = message.chat.id
    if chat_id not in GAMES:
        return await message.reply("No UNO lobby here.")
    g = GAMES[chat_id]
    uid = message.from_user.id
    if uid not in g["players"]:
        return await message.reply("You are not in this lobby.")
    g["players"].remove(uid)
    g["hands"].pop(uid, None)
    await message.reply(f"{message.from_user.mention} left the lobby.")
    # if less than 2 players and active, end game
    if g.get("active") and len(g["players"]) < 2:
        if g.get("timeout_task"):
            g["timeout_task"].cancel()
        del GAMES[chat_id]
        await message.reply("Not enough players. Game ended.")

@app.on_message(filters.command("startuno") & ~filters.private)
async def cmd_start(_, message: Message):
    chat_id = message.chat.id
    if chat_id not in GAMES:
        return await message.reply("No lobby found. Use /new first.")
    g = GAMES[chat_id]
    if g.get("active"):
        return await message.reply("Game already started.")
    if len(g["players"]) < 2:
        return await message.reply("Need at least 2 players to start.")
    # deal hands
    for pid in g["players"]:
        g["hands"][pid] = [g["deck"].pop() for _ in range(HAND_SIZE)]
    # ensure first discard not W4 for simplicity
    top = g["deck"].pop()
    while top == "W4":
        g["deck"].insert(0, top)
        random.shuffle(g["deck"])
        top = g["deck"].pop()
    g["discard"].append(top)
    g["current_color"] = top.split("_")[0] if "_" in top else None
    g["active"] = True
    g["turn_index"] = 0
    await message.reply(f"🎮 UNO started! First card: {top} ({code_to_label(top)})")
    await announce_turn(chat_id)

@app.on_message(filters.command("skip") & ~filters.private)
async def cmd_skip(_, message: Message):
    chat_id = message.chat.id
    if chat_id not in GAMES or not GAMES[chat_id].get("active"):
        return await message.reply("No active game.")
    g = GAMES[chat_id]
    # allow skip by command only when someone is AFK: advance turn
    if message.from_user.id not in g["players"]:
        return await message.reply("Only players can skip.")
    # skip current player if requester is not current player
    curr = g["players"][g["turn_index"]]
    if curr == message.from_user.id:
        return await message.reply("You can't skip yourself.")
    # skip current
    g["turn_index"] = (g["turn_index"] + 1) % len(g["players"])
    await message.reply("Player skipped due to timeout/request.")
    await announce_turn(chat_id)

# ---------------- notify_me command (PM notifications) ----------------
@app.on_message(filters.command("notify_me") & filters.private)
async def cmd_notify_me(_, message: Message):
    uid = message.from_user.id
    NOTIFY_USERS.add(uid)
    await message.reply("🛎 You will receive a private message when a new UNO lobby is created.")

@app.on_message(filters.command("stop_notify") & filters.private)
async def cmd_stop_notify(_, message: Message):
    uid = message.from_user.id
    NOTIFY_USERS.discard(uid)
    await message.reply("🔕 You will no longer receive notifications for new UNO lobbies.")

# ---------------- load sticker set helper (admin) ----------------
@app.on_message(filters.command("load_unostickers") & filters.user())  # allow bot owner only if needed, adjust filter
async def cmd_load_unostickers(_, message: Message):
    parts = message.text.split()
    set_name = parts[1] if len(parts) > 1 else DEFAULT_STICKER_SET
    mapped, msg = await load_uno_stickers(set_name)
    await message.reply(f"Sticker load result: {msg}\nTotal keys: {len(STICKER_MAP)}\nPreview keys:\n{sticker_keys_preview()}")

# ---------------- announce turn, build inline keyboard ----------------
def build_hand_keyboard(chat_id: int, player_id: int) -> InlineKeyboardMarkup:
    g = GAMES[chat_id]
    hand = g["hands"].get(player_id, [])
    top = g["discard"][-1]
    buttons = []
    # create row of up to 4 buttons per row
    row = []
    for i, card in enumerate(hand):
        label = code_to_label(card)  # textual label (fallback)
        cb = f"UNO:{chat_id}:PLAY:{player_id}:{i}"
        row.append(InlineKeyboardButton(label, callback_data=cb))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    # bottom row: draw, pass, state
    buttons.append([
        InlineKeyboardButton("🃏 Draw", callback_data=f"UNO:{chat_id}:DRAW:{player_id}:0"),
        InlineKeyboardButton("⏭ Pass", callback_data=f"UNO:{chat_id}:PASS:{player_id}:0"),
        InlineKeyboardButton("❓ State", callback_data=f"UNO:{chat_id}:STATE:{player_id}:0"),
    ])
    return InlineKeyboardMarkup(buttons)

async def announce_turn(chat_id: int):
    g = GAMES.get(chat_id)
    if not g or not g.get("active"):
        return
    player_id = g["players"][g["turn_index"]]
    top = g["discard"][-1]
    # if stickers loaded and mapping has top card, send sticker preview
    # we'll send a short message + inline keyboard for the current player
    text = f"🎴 UNO — Turn: <a href='tg://user?id={player_id}'>{(await app.get_users(player_id)).first_name}</a>\nTop: {code_to_label(top)}"
    kbd = build_hand_keyboard(chat_id, player_id)
    # cancel previous timeout
    if g.get("timeout_task"):
        g["timeout_task"].cancel()
    sent = await app.send_message(chat_id, text, parse_mode=enums.ParseMode.HTML, reply_markup=kbd)
    g["timeout_task"] = asyncio.create_task(turn_timeout(chat_id, sent.message_id))

async def turn_timeout(chat_id: int, message_id: int):
    await asyncio.sleep(TURN_TIMEOUT)
    g = GAMES.get(chat_id)
    if not g or not g.get("active"):
        return
    curr = g["players"][g["turn_index"]]
    # auto-draw one card and advance
    card = g["deck"].pop() if g["deck"] else None
    if card:
        g["hands"][curr].append(card)
        try:
            await app.send_message(chat_id, f"<a href='tg://user?id={curr}'>{(await app.get_users(curr)).first_name}</a> timed out and drew a card.", parse_mode=enums.ParseMode.HTML)
        except:
            pass
    # advance turn
    g["turn_index"] = (g["turn_index"] + 1) % len(g["players"])
    await announce_turn(chat_id)

# ---------------- core: validate playable ----------------
def is_playable(card: str, top_card: str, current_color: Optional[str]) -> bool:
    # wilds always playable
    if card in ("WILD","W4"):
        return True
    if top_card in ("WILD","W4"):
        # use current_color override if set
        top_color = current_color if current_color else None
    else:
        top_color = top_card.split("_")[0]
    c_color, c_val = card.split("_")
    if top_color and c_color == top_color:
        return True
    # match value
    top_val = top_card.split("_")[1] if "_" in top_card else top_card
    if c_val == top_val:
        return True
    return False

# ---------------- callback handler for inline actions ----------------
@app.on_callback_query(filters.regex(r"^UNO:"))
async def uno_callback(_, cq: CallbackQuery):
    # format UNO:chat:ACTION:player:payload
    parts = cq.data.split(":")
    try:
        chat_id = int(parts[1]); action = parts[2]; player = int(parts[3]); payload = parts[4]
    except:
        return await cq.answer("Invalid callback data.", show_alert=True)
    g = GAMES.get(chat_id)
    if not g or not g.get("active"):
        return await cq.answer("No active UNO game.", show_alert=True)
    current = g["players"][g["turn_index"]]
    # only the current player can use PLAY/DRAW/PASS buttons
    if player != current and action in ("PLAY","DRAW","PASS"):
        return await cq.answer("Not your turn.", show_alert=True)

    if action == "STATE":
        top = g["discard"][-1]
        return await cq.answer(f"Top: {code_to_label(top)}\nPlayers: {len(g['players'])}\nCurrent color: {g.get('current_color')}", show_alert=True)

    if action == "DRAW":
        # draw one
        if not g["deck"]:
            # reshuffle
            top = g["discard"].pop()
            g["deck"] = g["discard"]
            random.shuffle(g["deck"])
            g["discard"] = [top]
        card = g["deck"].pop()
        g["hands"][player].append(card)
        await cq.answer("You drew a card.")
        # edit the previously sent message so player can play drawn card as well
        await cq.message.edit_text("Card drawn. Choose your move.", reply_markup=build_hand_keyboard(chat_id, player))
        return

    if action == "PASS":
        # simply advance
        g["turn_index"] = (g["turn_index"] + 1) % len(g["players"])
        await cq.answer("Passed.")
        await announce_turn(chat_id)
        return

    if action == "PLAY":
        idx = int(payload)
        hand = g["hands"][player]
        if idx < 0 or idx >= len(hand):
            return await cq.answer("Invalid card.", show_alert=True)
        card = hand[idx]
        top = g["discard"][-1]
        if not is_playable(card, top, g.get("current_color")):
            return await cq.answer("You cannot play that card.", show_alert=True)
        # handle wild: ask color choice
        if card in ("WILD","W4"):
            color_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 Red", callback_data=f"UNO:{chat_id}:COLOR:{player}:R"),
                 InlineKeyboardButton("🔵 Blue", callback_data=f"UNO:{chat_id}:COLOR:{player}:B")],
                [InlineKeyboardButton("🟢 Green", callback_data=f"UNO:{chat_id}:COLOR:{player}:G"),
                 InlineKeyboardButton("🟡 Yellow", callback_data=f"UNO:{chat_id}:COLOR:{player}:Y")]
            ])
            return await cq.message.edit_text("Choose a color for your Wild card:", reply_markup=color_kb)

        # normal play
        played = g["hands"][player].pop(idx)
        g["discard"].append(played)
        g["current_color"] = played.split("_")[0] if "_" in played else None
        # special effects
        val = played.split("_")[1] if "_" in played else None
        if val == "SKIP":
            g["turn_index"] = (g["turn_index"] + 2) % len(g["players"])
        elif val == "REV":
            g["direction"] *= -1
            # switching direction; maintain index correctly
            g["turn_index"] = (g["turn_index"] + g["direction"]) % len(g["players"])
        elif val == "+2":
            # give next player 2 cards
            next_idx = (g["turn_index"] + 1) % len(g["players"])
            next_pid = g["players"][next_idx]
            for _ in range(2):
                if not g["deck"]:
                    top = g["discard"].pop()
                    g["deck"] = g["discard"]; random.shuffle(g["deck"]); g["discard"] = [top]
                g["hands"][next_pid].append(g["deck"].pop())
            g["turn_index"] = (g["turn_index"] + 2) % len(g["players"])
        else:
            # normal advance
            g["turn_index"] = (g["turn_index"] + 1) % len(g["players"])

        # win check
        if len(g["hands"][player]) == 0:
            await cq.message.reply_text(f"🏆 {(await app.get_users(player)).first_name} WON the UNO game!")
            if g.get("timeout_task"):
                g["timeout_task"].cancel()
            del GAMES[chat_id]
            return

        await cq.answer("Card played.")
        await announce_turn(chat_id)
        return

    if action == "COLOR":
        # payload is chosen color letter R/G/B/Y
        chosen = payload
        g["current_color"] = chosen
        # if last played was W4 then next player draws 4
        top = g["discard"][-1]
        if top == "W4":
            next_idx = (g["turn_index"] + 1) % len(g["players"])
            next_pid = g["players"][next_idx]
            for _ in range(4):
                if not g["deck"]:
                    t = g["discard"].pop(); g["deck"] = g["discard"]; random.shuffle(g["deck"]); g["discard"]=[t]
                g["hands"][next_pid].append(g["deck"].pop())
            # skip that player's turn
            g["turn_index"] = (g["turn_index"] + 2) % len(g["players"])
            await cq.answer("Color set and next player drew 4.")
        else:
            g["turn_index"] = (g["turn_index"] + 1) % len(g["players"])
            await cq.answer("Color set.")
        await announce_turn(chat_id)
        return

    await cq.answer("Unknown action.", show_alert=True)

# ---------------- small helper commands ----------------
@app.on_message(filters.command("myhand") & filters.private)
async def cmd_myhand(_, message: Message):
    # send player's current hand privately (if in a running game)
    uid = message.from_user.id
    # find game where user participates
    for chat_id, g in GAMES.items():
        if uid in g.get("players", []):
            hand = g["hands"].get(uid, [])
            text = "Your UNO hand:\n" + "\n".join(f"{i+1}. {code_to_label(c)}" for i, c in enumerate(hand))
            return await message.reply(text)
    await message.reply("You are not in any active UNO game.")

@app.on_message(filters.command("stopgame") & filters.user())  # bot owner / admin only if needed
async def cmd_stopgame(_, message: Message):
    chat_id = message.chat.id
    if chat_id in GAMES:
        if GAMES[chat_id].get("timeout_task"):
            GAMES[chat_id]["timeout_task"].cancel()
        del GAMES[chat_id]
        await message.reply("UNO game terminated.")
    else:
        await message.reply("No UNO game here.")

# ---------------- end of module ----------------
