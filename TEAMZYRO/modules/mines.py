import asyncio
import random
import uuid
import math
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import ZYRO as bot, user_collection, mines_collection, multi_collection, txn_collection 

# ---------------- Helpers ---------------- #
async def get_balance(uid: int) -> int:
    u = await user_collection.find_one({"id": uid}, {"balance": 1})
    return int(u.get("balance", 0)) if u else 0

def build_board_kb(grid:int, opened:set, game_id:str, prefix="mplay"):
    """Return InlineKeyboardMarkup for a grid (single or multi). prefix decides callback_data root."""
    buttons = []
    total = grid * grid
    for i in range(total):
        if i in opened:
            text = "✅"
        else:
            text = "⬜"
        buttons.append(InlineKeyboardButton(text, callback_data=f"{prefix}:{game_id}:{i}"))
    rows = [buttons[i:i+grid] for i in range(0, total, grid)]
    return InlineKeyboardMarkup(rows)

def build_board_kb_with_cash(grid:int, opened:set, game_id:str):
    kb = build_board_kb(grid, opened, game_id, prefix="mplay")
    # convert to list of lists, append cashout row
    # Pyrogram InlineKeyboardMarkup expects list of rows; create fresh list
    buttons = []
    total = grid * grid
    for i in range(total):
        if i in opened:
            text = "✅"
        else:
            text = "⬜"
        buttons.append(InlineKeyboardButton(text, callback_data=f"mplay:{game_id}:{i}"))
    rows = [buttons[i:i+grid] for i in range(0, total, grid)]
    rows.append([InlineKeyboardButton("💸 Cashout", callback_data=f"mcash:{game_id}")])
    return InlineKeyboardMarkup(rows)

def build_multiplayer_kb(grid:int, opened:set, cid:str):
    buttons = []
    total = grid * grid
    for i in range(total):
        if i in opened:
            text = "✅"
        else:
            text = "⬜"
        buttons.append(InlineKeyboardButton(text, callback_data=f"mpplay:{cid}:{i}"))
    rows = [buttons[i:i+grid] for i in range(0, total, grid)]
    rows.append([InlineKeyboardButton("🔁 REFRESH", callback_data=f"mprefresh:{cid}")])
    return InlineKeyboardMarkup(rows)

# ---------------- Step 1: /mines <amount> -> show size buttons ---------------- #
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

    # create a pending request id (user must select grid size)
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

    await message.reply_text(
        f"Choose board size for bet {bet} coins:\n4x4 (easy) | 6x6 | 8x8 (hard)",
        reply_markup=kb
    )

# ---------------- Start single-player game when size selected ---------------- #
async def start_single_game(client, cq, req_doc, grid:int):
    user_id = req_doc["user_id"]
    bet = int(req_doc["bet"])

    # double-check pending and balance
    fresh = await mines_collection.find_one({"req_id": req_doc["req_id"], "type": "pending_req"})
    if not fresh:
        return await cq.answer("❌ Request expired!", show_alert=True)

    bal = await get_balance(user_id)
    if bal < bet:
        # cleanup
        await mines_collection.delete_one({"req_id": req_doc["req_id"]})
        return await cq.answer("🚨 Insufficient balance to start game", show_alert=True)

    # deduct bet immediately
    await user_collection.update_one({"id": user_id}, {"$inc": {"balance": -bet}}, upsert=True)

    total_cells = grid * grid
    # choose number of mines: make it proportional to grid (for fun)
    if grid == 4:
        mines = 4
    elif grid == 6:
        mines = 6
    else:  # 8
        mines = 8

    mine_positions = random.sample(range(total_cells), mines)

    game_id = uuid.uuid4().hex[:10]
    game_doc = {
        "game_id": game_id,
        "type": "single_game",
        "user_id": user_id,
        "bet": bet,
        "grid": grid,
        "mines": mine_positions,
        "opened": [],      # list of ints
        "multiplier": 1.00,
        "created_at": datetime.utcnow(),
        "active": True
    }

    await mines_collection.insert_one(game_doc)
    # remove pending_req doc
    await mines_collection.delete_one({"req_id": req_doc["req_id"]})

    # send board
    kb = build_board_kb_with_cash(grid, set(), game_id)
    await cq.message.reply_text(
        f"🎮 Mines started — {grid}x{grid}\nBet: {bet} coins\nTap a box. Cashout anytime.",
        reply_markup=kb
    )
    try:
        await cq.answer()  # acknowledge original press
    except:
        pass

# ---------------- Single-player tile press ---------------- #
async def handle_single_press(client, cq, game_id, cell_index:int):
    try:
        game = await mines_collection.find_one({"game_id": game_id, "type": "single_game", "active": True})
        if not game:
            return await cq.answer("⚠️ Game not found or already finished", show_alert=True)
        if cq.from_user.id != game["user_id"]:
            return await cq.answer("⚠️ This is not your game", show_alert=True)

        opened = set(game.get("opened", []))
        if cell_index in opened:
            return await cq.answer("⏳ Already opened")

        # mark opened
        opened.add(cell_index)

        # hit mine?
        if cell_index in game["mines"]:
            # reveal board and end game (user loses; bet already deducted earlier)
            await mines_collection.update_one({"game_id": game_id}, {"$set": {"active": False, "opened": list(opened)}})
            kb = build_board_kb(game["grid"], opened, game_id, prefix="mplay")
            # reveal mines visually by editing message — we'll replace unopened cells with ❎, mines with 💣
            # Construct textual board representation for clarity
            try:
                text = f"💥 BOOM! You hit a mine.\nYou lost: {game['bet']} coins"
                # edit existing message (best-effort)
                await cq.message.edit_text(text, reply_markup=kb)
            except:
                await cq.message.reply_text(text, reply_markup=kb)
            return await cq.answer("💥 Mine hit!", show_alert=True)

        # safe hit: increase multiplier (example: +0.05 per safe)
        new_mult = round(float(game.get("multiplier", 1.0)) + 0.05, 2)
        await mines_collection.update_one({"game_id": game_id}, {"$set": {"opened": list(opened), "multiplier": new_mult}})

        # potential payout
        potential = math.floor(game["bet"] * new_mult)

        kb = build_board_kb_with_cash(game["grid"], opened, game_id)
        status = f"🎮 Mines\nBet: {game['bet']} | Opened: {len(opened)}/{game['grid']*game['grid']} | Mult: {new_mult:.2f}x\nPotential: {potential} coins"
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

# ---------------- Single-player Cashout ---------------- #
async def handle_single_cashout(client, cq, game_id):
    try:
        game = await mines_collection.find_one({"game_id": game_id, "type": "single_game", "active": True})
        if not game:
            return await cq.answer("⚠️ No active game", show_alert=True)
        if cq.from_user.id != game["user_id"]:
            return await cq.answer("⚠️ Not your game", show_alert=True)

        payout = math.floor(game["bet"] * float(game.get("multiplier", 1.0)))
        # mark inactive and credit user
        await mines_collection.update_one({"game_id": game_id}, {"$set": {"active": False}})
        await user_collection.update_one({"id": cq.from_user.id}, {"$inc": {"balance": payout}}, upsert=True)

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

# ---------------- Multiplayer challenge: /mchallenge <bet> @user or reply ---------------- #
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
            opponent_user = await client.get_users(target)
            opponent = opponent_user
        except:
            return await message.reply_text("❌ Could not resolve user. Tag or reply to a user.")

    if opponent.id == challenger.id:
        return await message.reply_text("❌ Cannot challenge yourself")

    # check balances quickly
    bal_c = await get_balance(challenger.id)
    bal_o = await get_balance(opponent.id)
    if bal_c < bet:
        return await message.reply_text("🚨 You don't have enough to challenge")
    if bal_o < bet:
        return await message.reply_text("🚨 Opponent doesn't have enough coins")

    cid = uuid.uuid4().hex[:8]
    # store pending challenge
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
    # send private invite to opponent
    try:
        await client.send_message(opponent.id, f"🎮 Challenge from {challenger.first_name}\nBet: {bet} coins\nAccept or Decline", reply_markup=kb)
    except Exception as e:
        print("CHALLENGE SEND FAIL:", e)
        # cleanup
        await multi_collection.delete_one({"cid": cid})
        return await message.reply_text("⚠ Could not send challenge (opponent may have PMs closed)")

    await message.reply_text(f"Challenge sent to {opponent.first_name} (cid: {cid}) — waiting for accept")

# ---------------- Multiplayer accept/reject handlers & size selection ---------------- #
async def mch_reject(client, cq, cid):
    doc = await multi_collection.find_one({"cid": cid, "type": "challenge", "status": "pending"})
    if not doc:
        return await cq.answer("⚠ Challenge expired", show_alert=True)
    if cq.from_user.id != doc["opponent"]:
        return await cq.answer("⚠ This invite is not for you", show_alert=True)
    await multi_collection.update_one({"cid": cid}, {"$set": {"status": "rejected"}})
    await cq.message.edit_text("❌ Challenge Declined")
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

    # send size selection (we'll reuse a similar flow: 3x3,9x9,12x12)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("4 x 4", callback_data=f"mch:size:{cid}:3")],
        [InlineKeyboardButton("6 x 6", callback_data=f"mch:size:{cid}:9")],
        [InlineKeyboardButton("8 x 8", callback_data=f"mch:size:{cid}:12")]
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

    # re-check balances
    bal_c = await get_balance(challenger)
    bal_o = await get_balance(opponent)
    if bal_c < bet or bal_o < bet:
        await multi_collection.update_one({"cid": cid}, {"$set": {"status": "failed", "reason": "insufficient"}})
        return await cq.answer("🚨 One of players has insufficient balance", show_alert=True)

    # deduct bets for both
    await user_collection.update_one({"id": challenger}, {"$inc": {"balance": -bet}}, upsert=True)
    await user_collection.update_one({"id": opponent}, {"$inc": {"balance": -bet}}, upsert=True)

    # create multiplayer game doc
    total_cells = grid_choice * grid_choice
    if grid_choice == 3:
        mines = 3
    elif grid_choice == 6:
        mines = 6
    else:
        mines = 8

    mine_positions = random.sample(range(total_cells), mines)
    game = {
        "cid": cid,
        "type": "multi_game",
        "players": [challenger, opponent],
        "bet": bet,
        "grid": grid_choice,
        "mines": mine_positions,
        "opened": [],
        "turn": challenger,  # challenger starts
        "active": True,
        "created_at": datetime.utcnow()
    }
    await multi_collection.update_one({"cid": cid}, {"$set": game, "$unset": {"status": ""}}, upsert=True)

    # notify both players: build board keyboard
    kb = build_multiplayer_kb(grid_choice, set(), cid)
    status = f"🎮 Mines Duel STARTED!\nBet each: {bet} | Pool: {bet*2}\nGrid: {grid_choice}x{grid_choice}\nTurn: Player (id {game['turn']})"
    # send to opponent (where selection happened) and challenger
    try:
        await cq.message.edit_text("Match started! Check your private message for board.")
    except:
        pass
    # DM challenger
    try:
        await client.send_message(challenger, status, reply_markup=kb)
    except:
        pass
    # DM opponent
    try:
        await client.send_message(opponent, status, reply_markup=kb)
    except:
        pass
    return await cq.answer("Match started ✅")

# ---------------- Multiplayer play handler ---------------- #
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

    # mine?
    if cell_idx in doc["mines"]:
        # other player wins pool
        other = [p for p in doc["players"] if p != player][0]
        pool = doc["bet"] * 2
        await user_collection.update_one({"id": other}, {"$inc": {"balance": pool}}, upsert=True)
        await multi_collection.update_one({"cid": cid}, {"$set": {"active": False, "opened": list(opened)}})
        kb = build_multiplayer_kb(doc["grid"], opened, cid)
        text = f"💥 Player {player} hit a mine!\n🏆 Player {other} wins the pool: {pool} coins"
        try:
            await cq.message.edit_text(text, reply_markup=kb)
        except:
            await client.send_message(player, text, reply_markup=kb)
        # notify other
        try:
            await client.send_message(other, f"🏆 You won {pool} coins! Opponent hit a mine.")
        except:
            pass
        return await cq.answer("💥 Mine! Opponent wins", show_alert=True)

    # safe: mark opened and switch turn
    await multi_collection.update_one({"cid": cid}, {"$set": {"opened": list(opened), "turn": [p for p in doc["players"] if p != player][0]}})
    new_turn = [p for p in doc["players"] if p != player][0]
    kb = build_multiplayer_kb(doc["grid"], opened, cid)
    status = f"🎮 Mines Duel\nPool: {doc['bet']*2} | Opened: {len(opened)}/{doc['grid']*doc['grid']}\nTurn: {new_turn}"
    try:
        await cq.message.edit_text(status, reply_markup=kb)
    except:
        # best effort: DM both players
        for p in doc["players"]:
            try:
                await client.send_message(p, status, reply_markup=kb)
            except:
                pass
    return await cq.answer("✅ Safe")

# ---------------- Multiplayer refresh ---------------- #
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

# ---------------- Universal callback router ---------------- #
@bot.on_callback_query()
async def universal_router(client, cq):
    data = cq.data or ""
    # debug log
    try:
        print(f"[CALLBACK] {cq.from_user.id} -> {data}")
    except:
        pass

    # mines pending request -> size selection
    if data.startswith("mines:req:"):
        # format: mines:req:<rid>:<grid>
        parts = data.split(":")
        if len(parts) != 4:
            return await cq.answer("⚠ Invalid", show_alert=True)
        _, _, rid, grid_s = parts
        # find pending req
        req = await mines_collection.find_one({"req_id": rid, "type": "pending_req"})
        if not req:
            return await cq.answer("⚠ Request expired or invalid", show_alert=True)
        if cq.from_user.id != req["user_id"]:
            return await cq.answer("⚠ Not your selection", show_alert=True)
        try:
            grid = int(grid_s)
        except:
            return await cq.answer("⚠ Invalid grid", show_alert=True)
        # start single game
        return await start_single_game(client, cq, req, grid)

    # single-player play
    if data.startswith("mplay:"):
        # format mplay:<game_id>:<cell>
        parts = data.split(":")
        if len(parts) != 3:
            return await cq.answer("⚠ Invalid", show_alert=True)
        _, gid, cell = parts
        try:
            ci = int(cell)
        except:
            return await cq.answer("⚠ Invalid cell", show_alert=True)
        return await handle_single_press(client, cq, gid, ci)

    # single-player cashout
    if data.startswith("mcash:"):
        # mcash:<game_id>
        parts = data.split(":")
        if len(parts) != 2:
            return await cq.answer("⚠ Invalid", show_alert=True)
        _, gid = parts
        return await handle_single_cashout(client, cq, gid)

    # multiplayer challenge accept/reject/size
    if data.startswith("mch:rej:"):
        cid = data.split(":")[2]
        return await mch_reject(client, cq, cid)
    if data.startswith("mch:acc:"):
        cid = data.split(":")[2]
        return await mch_accept(client, cq, cid)
    if data.startswith("mch:size:"):
        # mch:size:<cid>:<grid>
        parts = data.split(":")
        if len(parts) != 4:
            return await cq.answer("⚠ Invalid", show_alert=True)
        cid = parts[2]; grid = int(parts[3])
        return await mch_size_selected(client, cq, cid, grid)

    # multiplayer gameplay
    if data.startswith("mpplay:"):
        # mpplay:<cid>:<cell>
        parts = data.split(":")
        if len(parts) != 3:
            return await cq.answer("⚠ Invalid", show_alert=True)
        cid = parts[1]; cell = int(parts[2])
        return await handle_mp_play(client, cq, cid, cell)

    if data.startswith("mprefresh:"):
        cid = data.split(":")[1]
        return await handle_mp_refresh(client, cq, cid)

    # fallback
    try:
        return await cq.answer("⚠ Unknown or expired button", show_alert=True)
    except:
        pass
