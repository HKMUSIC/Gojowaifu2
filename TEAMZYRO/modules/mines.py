import asyncio
import random
import uuid
import math
from datetime import datetime
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import ZYRO as bot, user_collection, mines_collection, multi_collection, txn_collection

# ---------------- Helpers ---------------- #
async def get_balance(uid: int) -> int:
    u = await user_collection.find_one({"id": uid}, {"balance": 1})
    return int(u.get("balance", 0)) if u else 0

async def change_balance(uid: int, delta: int, reason: str, meta: dict = None):
    """Change balance and log transaction to txn_collection."""
    await user_collection.update_one({"id": uid}, {"$inc": {"balance": delta}}, upsert=True)
    tx = {
        "tx_id": uuid.uuid4().hex[:12],
        "user_id": uid,
        "amount": int(delta),
        "reason": reason,
        "meta": meta or {},
        "timestamp": datetime.utcnow()
    }
    try:
        await txn_collection.insert_one(tx)
    except Exception as e:
        print("TX LOG FAIL:", e)
    return tx

def index_to_rc(index: int, grid: int):
    return divmod(index, grid)  # (row, col)

def rc_to_index(r: int, c: int, grid: int):
    return r * grid + c

def compute_adjacent_counts(grid: int, mines: set):
    """Return dict index -> adjacent mine count"""
    counts = {}
    total = grid * grid
    for i in range(total):
        r, c = index_to_rc(i, grid)
        cnt = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < grid and 0 <= nc < grid:
                    ni = rc_to_index(nr, nc, grid)
                    if ni in mines:
                        cnt += 1
        counts[i] = cnt
    return counts

def _cell_label(i:int, opened:set, mines:set, counts:dict, reveal_mines:bool=False):
    """Return label for a cell for keyboard building."""
    if reveal_mines and i in mines:
        return "💣"
    if i in opened:
        val = counts.get(i, 0)
        if val == 0:
            return "▫️"  # empty
        else:
            return str(val)
    return "⬜"

def build_board_kb(grid:int, opened:set, game_id:str, prefix="mplay", mines:set=None, reveal_mines:bool=False):
    mines = set(mines or [])
    counts = compute_adjacent_counts(grid, mines)
    buttons = []
    total = grid * grid
    for i in range(total):
        text = _cell_label(i, opened, mines, counts, reveal_mines=reveal_mines)
        buttons.append(InlineKeyboardButton(text, callback_data=f"{prefix}:{game_id}:{i}"))
    rows = [buttons[i:i+grid] for i in range(0, total, grid)]
    return InlineKeyboardMarkup(rows)

def build_board_kb_with_cash(grid:int, opened:set, game_id:str, mines:set=None, reveal_mines:bool=False):
    """Single-player board with cashout button"""
    mines = set(mines or [])
    counts = compute_adjacent_counts(grid, mines)
    rows = []
    total = grid * grid
    row = []
    for i in range(total):
        row.append(InlineKeyboardButton(_cell_label(i, opened, mines, counts, reveal_mines), callback_data=f"mplay:{game_id}:{i}"))
        if len(row) == grid:
            rows.append(row)
            row = []
    rows.append([InlineKeyboardButton("💸 Cashout", callback_data=f"mcash:{game_id}")])
    return InlineKeyboardMarkup(rows)

def build_multiplayer_kb(grid:int, opened:set, cid:str, mines:set=None, reveal_mines:bool=False):
    mines = set(mines or [])
    counts = compute_adjacent_counts(grid, mines)
    buttons = []
    total = grid * grid
    for i in range(total):
        buttons.append(InlineKeyboardButton(_cell_label(i, opened, mines, counts, reveal_mines), callback_data=f"mpplay:{cid}:{i}"))
    rows = [buttons[i:i+grid] for i in range(0, total, grid)]
    rows.append([InlineKeyboardButton("🔁 REFRESH", callback_data=f"mprefresh:{cid}")])
    return InlineKeyboardMarkup(rows)

# ---------------- Single-player: /mines <bet> ---------------- #
@bot.on_message(filters.command("mines"))
async def mines_menu(client, message):
    args = message.text.split()
    user_id = message.from_user.id

    if len(args) < 2:
        return await message.reply_text("Usage: /mines <bet_amount>\nExample: /mines 100")

    try:
        bet = int(args[1])
    except:
        return await message.reply_text("❌ Invalid bet amount")

    if bet <= 0:
        return await message.reply_text("❌ Bet must be > 0")

    bal = await get_balance(user_id)
    if bal < bet:
        return await message.reply_text(f"🚨 Insufficient balance. Your balance: {bal} coins")

    rid = uuid.uuid4().hex[:8]
    await mines_collection.insert_one({
        "req_id": rid,
        "type": "pending_req",
        "user_id": user_id,
        "bet": bet,
        "created_at": datetime.utcnow()
    })

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("4 x 4", callback_data=f"mines:req:{rid}:4")],
        [InlineKeyboardButton("6 x 6", callback_data=f"mines:req:{rid}:6")],
        [InlineKeyboardButton("8 x 8", callback_data=f"mines:req:{rid}:8")]
    ])

    await message.reply_text(f"Choose board size for bet {bet} coins:\n4x4 | 6x6 | 8x8", reply_markup=kb)

async def start_single_game(client, cq, req_doc, grid:int):
    user_id = req_doc["user_id"]
    bet = int(req_doc["bet"])

    fresh = await mines_collection.find_one({"req_id": req_doc["req_id"], "type": "pending_req"})
    if not fresh:
        return await cq.answer("❌ Request expired!", show_alert=True)

    bal = await get_balance(user_id)
    if bal < bet:
        await mines_collection.delete_one({"req_id": req_doc["req_id"]})
        return await cq.answer("🚨 Insufficient balance", show_alert=True)

    # deduct bet and log
    await change_balance(user_id, -bet, "mines_bet", {"game": "single", "bet": bet})
    total_cells = grid * grid
    # mines proportional: 4->4, 6->6, 8->10 (slightly harder)
    if grid == 4:
        mines_count = 3
    elif grid == 6:
        mines_count = 6
    else:
        mines_count = 10

    mine_positions = random.sample(range(total_cells), mines_count)
    game_id = uuid.uuid4().hex[:10]
    game_doc = {
        "game_id": game_id,
        "type": "single_game",
        "user_id": user_id,
        "bet": bet,
        "grid": grid,
        "mines": mine_positions,
        "opened": [],
        "multiplier": 1.00,
        "created_at": datetime.utcnow(),
        "active": True
    }

    await mines_collection.insert_one(game_doc)
    await mines_collection.delete_one({"req_id": req_doc["req_id"]})

    kb = build_board_kb_with_cash(grid, set(), game_id)
    await cq.message.reply_text(f"🎮 Mines started — {grid}x{grid}\nBet: {bet} coins\nTap a box. Cashout anytime.", reply_markup=kb)
    try:
        await cq.answer()
    except:
        pass

# ---------------- Single-player press & cashout ---------------- #
async def handle_single_press(client, cq, game_id, cell_index:int):
    try:
        game = await mines_collection.find_one({"game_id": game_id, "type": "single_game", "active": True})
        if not game:
            return await cq.answer("⚠️ Game not found or finished", show_alert=True)
        if cq.from_user.id != game["user_id"]:
            return await cq.answer("⚠️ Not your game", show_alert=True)
        opened = set(game.get("opened", []))
        if cell_index in opened:
            return await cq.answer("⏳ Already opened")
        opened.add(cell_index)

        mines_set = set(game["mines"])
        # hit mine
        if cell_index in mines_set:
            # lose: game over
            await mines_collection.update_one({"game_id": game_id}, {"$set": {"active": False, "opened": list(opened)}})
            # no refund; log loss (bet already deducted)
            await txn_collection.insert_one({
                "tx_id": uuid.uuid4().hex[:12],
                "user_id": cq.from_user.id,
                "amount": -int(game["bet"]),
                "reason": "mines_loss",
                "meta": {"game_id": game_id, "grid": game["grid"]},
                "timestamp": datetime.utcnow()
            })
            kb = build_board_kb_with_cash(game["grid"], opened, game_id, mines=set(game["mines"]), reveal_mines=True)
            text = f"💥 BOOM! You hit a mine.\nYou lost: {game['bet']} coins"
            try:
                await cq.message.edit_text(text, reply_markup=kb)
            except:
                await cq.message.reply_text(text, reply_markup=kb)
            return await cq.answer("💥 Mine hit!", show_alert=True)

        # safe: compute new multiplier (example exponential-ish)
        opened_count = len(opened)
        # multiplier: start 1.0, grow by 0.08 then + smaller increments (adjustable)
        new_mult = round(1.0 + opened_count * 0.08, 2)
        await mines_collection.update_one({"game_id": game_id}, {"$set": {"opened": list(opened), "multiplier": new_mult}})

        potential = math.floor(game["bet"] * new_mult)
        kb = build_board_kb_with_cash(game["grid"], opened, game_id)
        status = f"🎮 Mines\nBet: {game['bet']} | Opened: {opened_count}/{game['grid']*game['grid']} | Mult: {new_mult:.2f}x\nPotential: {potential} coins"
        try:
            await cq.message.edit_text(status, reply_markup=kb)
        except:
            await cq.message.reply_text(status, reply_markup=kb)
        return await cq.answer("✅ Safe!")
    except Exception as e:
        print("SINGLE PRESS ERROR:", e)
        try:
            return await cq.answer("⚠️ Error", show_alert=True)
        except:
            pass

async def handle_single_cashout(client, cq, game_id):
    try:
        game = await mines_collection.find_one({"game_id": game_id, "type": "single_game", "active": True})
        if not game:
            return await cq.answer("⚠️ No active game", show_alert=True)
        if cq.from_user.id != game["user_id"]:
            return await cq.answer("⚠️ Not your game", show_alert=True)

        payout = math.floor(game["bet"] * float(game.get("multiplier", 1.0)))
        await mines_collection.update_one({"game_id": game_id}, {"$set": {"active": False}})
        await change_balance(cq.from_user.id, payout, "mines_win", {"game_id": game_id, "grid": game["grid"], "payout": payout})

        # log txn
        await txn_collection.insert_one({
            "tx_id": uuid.uuid4().hex[:12],
            "user_id": cq.from_user.id,
            "amount": int(payout),
            "reason": "mines_cashout",
            "meta": {"game_id": game_id, "grid": game["grid"]},
            "timestamp": datetime.utcnow()
        })

        kb = build_board_kb(game["grid"], set(game.get("opened", [])), game_id, prefix="mplay")
        text = f"💸 Cashed out!\nYou won: {payout} coins\nNew balance updated."
        try:
            await cq.message.edit_text(text, reply_markup=kb)
        except:
            await cq.message.reply_text(text, reply_markup=kb)
        return await cq.answer(f"💸 +{payout} coins", show_alert=True)
    except Exception as e:
        print("SINGLE CASHOUT ERROR:", e)
        try:
            return await cq.answer("⚠️ Error cashing out", show_alert=True)
        except:
            pass

# ---------------- Multiplayer challenge (/mchallenge) ---------------- #
@bot.on_message(filters.command("mchallenge"))
async def mchallenge_cmd(client, message):
    args = message.text.split()
    challenger = message.from_user
    if len(args) < 2 and not message.reply_to_message:
        return await message.reply_text("Usage: /mchallenge <bet> @username\nOr reply to user's message with /mchallenge <bet>")

    try:
        bet = int(args[1])
    except:
        return await message.reply_text("❌ Invalid bet amount")

    if message.reply_to_message:
        opponent = message.reply_to_message.from_user
    else:
        if len(args) < 3:
            return await message.reply_text("Tag the opponent: /mchallenge <bet> @username")
        try:
            target = args[2].replace("@", "")
            opponent = await client.get_users(target)
        except:
            return await message.reply_text("❌ Could not resolve user. Tag or reply to a user.")

    if opponent.id == challenger.id:
        return await message.reply_text("❌ Cannot challenge yourself")

    bal_c = await get_balance(challenger.id)
    bal_o = await get_balance(opponent.id)
    if bal_c < bet:
        return await message.reply_text("🚨 You don't have enough to challenge")
    if bal_o < bet:
        return await message.reply_text("🚨 Opponent doesn't have enough coins")

    cid = uuid.uuid4().hex[:8]
    await multi_collection.insert_one({
        "cid": cid,
        "type": "challenge",
        "challenger": challenger.id,
        "opponent": opponent.id,
        "bet": bet,
        "created_at": datetime.utcnow(),
        "status": "pending"
    })

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ ACCEPT", callback_data=f"mch:acc:{cid}"),
         InlineKeyboardButton("❌ DECLINE", callback_data=f"mch:rej:{cid}")]
    ])
    try:
        await client.send_message(opponent.id, f"🎮 Challenge from {challenger.first_name}\nBet: {bet} coins\nAccept or Decline", reply_markup=kb)
    except Exception as e:
        print("CHALLENGE SEND FAIL:", e)
        await multi_collection.delete_one({"cid": cid})
        return await message.reply_text("⚠ Could not send challenge (opponent may have PMs closed)")

    await message.reply_text(f"Challenge sent to {opponent.first_name} (cid: {cid}) — waiting for accept")

async def mch_reject(client, cq, cid):
    doc = await multi_collection.find_one({"cid": cid, "type": "challenge", "status": "pending"})
    if not doc:
        return await cq.answer("⚠ Challenge expired", show_alert=True)
    if cq.from_user.id != doc["opponent"]:
        return await cq.answer("⚠ This invite is not for you", show_alert=True)
    await multi_collection.update_one({"cid": cid}, {"$set": {"status": "rejected"}})
    try:
        await cq.message.edit_text("❌ Challenge Declined")
    except:
        pass
    try:
        await client.send_message(doc["challenger"], f"Your challenge {cid} was declined by opponent.")
    except:
        pass
    return await cq.answer("Declined ✅")

async def mch_accept(client, cq, cid):
    doc = await multi_collection.find_one({"cid": cid, "type": "challenge", "status": "pending"})
    if not doc:
        return await cq.answer("⚠ Challenge expired", show_alert=True)
    if cq.from_user.id != doc["opponent"]:
        return await cq.answer("⚠ This invite is not for you", show_alert=True)

    # send size selection fixed values (4,6,8)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("4 x 4", callback_data=f"mch:size:{cid}:4")],
        [InlineKeyboardButton("6 x 6", callback_data=f"mch:size:{cid}:6")],
        [InlineKeyboardButton("8 x 8", callback_data=f"mch:size:{cid}:8")]
    ])
    try:
        await cq.message.edit_text("Select board size for multiplayer duel:", reply_markup=kb)
    except:
        await cq.message.reply_text("Select board size for multiplayer duel:", reply_markup=kb)
    return await cq.answer()

async def mch_size_selected(client, cq, cid, grid_choice:int):
    doc = await multi_collection.find_one({"cid": cid, "type": "challenge", "status": "pending"})
    if not doc:
        return await cq.answer("⚠ Challenge expired", show_alert=True)

    challenger = doc["challenger"]
    opponent = doc["opponent"]
    bet = doc["bet"]

    bal_c = await get_balance(challenger)
    bal_o = await get_balance(opponent)
    if bal_c < bet or bal_o < bet:
        await multi_collection.update_one({"cid": cid}, {"$set": {"status": "failed", "reason": "insufficient"}})
        return await cq.answer("🚨 One of players has insufficient balance", show_alert=True)

    # deduct both bets and log
    await change_balance(challenger, -bet, "mchallenge_bet", {"cid": cid})
    await change_balance(opponent, -bet, "mchallenge_bet", {"cid": cid})

    total_cells = grid_choice * grid_choice
    if grid_choice == 4:
        mines_count = 3
    elif grid_choice == 6:
        mines_count = 6
    else:
        mines_count = 10

    mine_positions = random.sample(range(total_cells), mines_count)
    game = {
        "cid": cid,
        "type": "multi_game",
        "players": [challenger, opponent],
        "bet": bet,
        "grid": grid_choice,
        "mines": mine_positions,
        "opened": [],
        "turn": challenger,
        "active": True,
        "created_at": datetime.utcnow()
    }
    await multi_collection.update_one({"cid": cid}, {"$set": game, "$unset": {"status": ""}}, upsert=True)

    kb = build_multiplayer_kb(grid_choice, set(), cid)
    status = f"🎮 Mines Duel STARTED!\nBet each: {bet} | Pool: {bet*2}\nGrid: {grid_choice}x{grid_choice}\nTurn: Player (id {game['turn']})"
    try:
        await cq.message.edit_text("Match started! Check your private message for board.")
    except:
        pass
    try:
        await client.send_message(challenger, status, reply_markup=kb)
    except:
        pass
    try:
        await client.send_message(opponent, status, reply_markup=kb)
    except:
        pass
    return await cq.answer("Match started ✅")

# ---------------- Multiplayer play / refresh ---------------- #
async def handle_mp_play(client, cq, cid, cell_idx:int):
    doc = await multi_collection.find_one({"cid": cid, "type": "multi_game", "active": True})
    if not doc:
        return await cq.answer("⚠ No active multi-game", show_alert=True)

    player = cq.from_user.id
    if player not in doc["players"]:
        return await cq.answer("⚠ You're not part of this match", show_alert=True)

    if player != doc["turn"]:
        return await cq.answer("⏳ Wait for your turn", show_alert=True)

    opened = set(doc.get("opened", []))
    if cell_idx in opened:
        return await cq.answer("⏳ Already opened")

    opened.add(cell_idx)
    mines_set = set(doc["mines"])

    # mine?
    if cell_idx in mines_set:
        other = [p for p in doc["players"] if p != player][0]
        pool = doc["bet"] * 2
        await change_balance(other, pool, "mchallenge_win", {"cid": cid, "winner": other, "loser": player})
        # mark finished
        await multi_collection.update_one({"cid": cid}, {"$set": {"active": False, "opened": list(opened)}})
        kb = build_multiplayer_kb(doc["grid"], opened, cid, mines=set(doc["mines"]), reveal_mines=True)
        text = f"💥 Player {player} hit a mine!\n🏆 Player {other} wins the pool: {pool} coins"
        try:
            await cq.message.edit_text(text, reply_markup=kb)
        except:
            await client.send_message(player, text, reply_markup=kb)
        try:
            await client.send_message(other, f"🏆 You won {pool} coins! Opponent hit a mine.")
        except:
            pass
        # log txns
        await txn_collection.insert_many([
            {"tx_id": uuid.uuid4().hex[:12], "user_id": other, "amount": pool, "reason": "mchallenge_win", "meta": {"cid": cid}, "timestamp": datetime.utcnow()},
            {"tx_id": uuid.uuid4().hex[:12], "user_id": player, "amount": -doc["bet"], "reason": "mchallenge_loss", "meta": {"cid": cid}, "timestamp": datetime.utcnow()}
        ])
        return await cq.answer("💥 Mine! Opponent wins", show_alert=True)

    # safe: mark opened and switch turn
    new_turn = [p for p in doc["players"] if p != player][0]
    await multi_collection.update_one({"cid": cid}, {"$set": {"opened": list(opened), "turn": new_turn}})
    kb = build_multiplayer_kb(doc["grid"], opened, cid)
    status = f"🎮 Mines Duel\nPool: {doc['bet']*2} | Opened: {len(opened)}/{doc['grid']*doc['grid']}\nTurn: {new_turn}"
    try:
        await cq.message.edit_text(status, reply_markup=kb)
    except:
        for p in doc["players"]:
            try:
                await client.send_message(p, status, reply_markup=kb)
            except:
                pass
    return await cq.answer("✅ Safe")

async def handle_mp_refresh(client, cq, cid):
    doc = await multi_collection.find_one({"cid": cid, "type": "multi_game"})
    if not doc:
        return await cq.answer("⚠ Match not found", show_alert=True)
    kb = build_multiplayer_kb(doc["grid"], set(doc.get("opened", [])), cid)
    status = f"🎮 Mines Duel\nPool: {doc['bet']*2} | Opened: {len(doc.get('opened', []))}/{doc['grid']*doc['grid']}\nTurn: {doc.get('turn')}"
    try:
        await cq.message.edit_text(status, reply_markup=kb)
    except:
        for p in doc["players"]:
            try:
                await client.send_message(p, status, reply_markup=kb)
            except:
                pass
    return await cq.answer("Refreshed ✅")

# ---------------- User stats command with cooldown ---------------- #
from datetime import datetime, timedelta

# store cooldowns in memory (simple dict: {user_id: datetime})
_mystats_cooldown = {}

@bot.on_message(filters.command("mystats"))
async def mystats_cmd(client, message):
    user_id = message.from_user.id
    now = datetime.utcnow()

    # check cooldown (10 seconds per user)
    last_used = _mystats_cooldown.get(user_id)
    if last_used and (now - last_used).total_seconds() < 10:
        remaining = 10 - int((now - last_used).total_seconds())
        return await message.reply_text(f"⏳ Please wait {remaining}s before using /mystats again.")

    _mystats_cooldown[user_id] = now  # update last usage time

    # Fetch user transactions related to mines
    cursor = txn_collection.find({"user_id": user_id})
    total_bets = total_wins = total_losses = games = 0

    async for tx in cursor:
        reason = tx.get("reason", "")
        amt = int(tx.get("amount", 0))
        if "bet" in reason:
            total_bets += abs(amt)
            games += 1
        elif "win" in reason or "cashout" in reason:
            total_wins += amt
        elif "loss" in reason:
            total_losses += abs(amt)

    net = total_wins - total_bets
    profit_emoji = "🟢" if net > 0 else ("🔴" if net < 0 else "⚪")

    msg = (
        f"📊 **Your Mines Stats**\n"
        f"🎮 Games Played: `{games}`\n"
        f"💰 Total Bet: `{total_bets}` coins\n"
        f"🏆 Total Won: `{total_wins}` coins\n"
        f"💥 Total Lost: `{total_losses}` coins\n"
        f"{profit_emoji} **Net Profit/Loss:** `{net}` coins"
    )

    await message.reply_text(msg)


    
                            
# ---------------- Universal callback router ---------------- #
@bot.on_callback_query()
async def universal_router(client, cq):
    data = cq.data or ""
    try:
        print(f"[CALLBACK] {cq.from_user.id} -> {data}")
    except:
        pass

    # mines pending request -> start single game
    if data.startswith("mines:req:"):
        parts = data.split(":")
        if len(parts) != 4:
            return await cq.answer("⚠ Invalid", show_alert=True)
        _, _, rid, grid_s = parts
        req = await mines_collection.find_one({"req_id": rid, "type": "pending_req"})
        if not req:
            return await cq.answer("⚠ Request expired or invalid", show_alert=True)
        if cq.from_user.id != req["user_id"]:
            return await cq.answer("⚠ Not your selection", show_alert=True)
        try:
            grid = int(grid_s)
        except:
            return await cq.answer("⚠ Invalid grid", show_alert=True)
        return await start_single_game(client, cq, req, grid)

    # single-player play
    if data.startswith("mplay:"):
        parts = data.split(":")
        if len(parts) != 3:
            return await cq.answer("⚠ Invalid", show_alert=True)
        _, gid, cell = parts
        try:
            ci = int(cell)
        except:
            return await cq.answer("⚠ Invalid cell", show_alert=True)
        return await handle_single_press(client, cq, gid, ci)

    # single cashout
    if data.startswith("mcash:"):
        parts = data.split(":")
        if len(parts) != 2:
            return await cq.answer("⚠ Invalid", show_alert=True)
        _, gid = parts
        return await handle_single_cashout(client, cq, gid)

    # multiplayer flows
    if data.startswith("mch:rej:"):
        cid = data.split(":")[2]
        return await mch_reject(client, cq, cid)
    if data.startswith("mch:acc:"):
        cid = data.split(":")[2]
        return await mch_accept(client, cq, cid)
    if data.startswith("mch:size:"):
        parts = data.split(":")
        if len(parts) != 4:
            return await cq.answer("⚠ Invalid", show_alert=True)
        cid = parts[2]
        try:
            grid = int(parts[3])
        except:
            return await cq.answer("⚠ Invalid grid", show_alert=True)
        return await mch_size_selected(client, cq, cid, grid)

    # multiplayer play
    if data.startswith("mpplay:"):
        parts = data.split(":")
        if len(parts) != 3:
            return await cq.answer("⚠ Invalid", show_alert=True)
        cid = parts[1]
        try:
            cell = int(parts[2])
        except:
            return await cq.answer("⚠ Invalid cell", show_alert=True)
        return await handle_mp_play(client, cq, cid, cell)

    if data.startswith("mprefresh:"):
        cid = data.split(":")[1]
        return await handle_mp_refresh(client, cq, cid)

    try:
        return await cq.answer("⚠ Unknown or expired button", show_alert=True)
    except:
        pass
    
