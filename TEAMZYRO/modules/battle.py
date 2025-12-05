# modules/battle.py
import random
import asyncio
from typing import Dict, Optional
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from TEAMZYRO import app, user_collection  # make sure these are exported from your bot package

# ====== assets ======
BATTLE_IMAGES = [
    "https://files.catbox.moe/1f6a2q.jpg",
    "https://files.catbox.moe/0o7nkl.jpg",
    "https://files.catbox.moe/3gljwk.jpg",
    "https://files.catbox.moe/5dtj1p.jpg",
]

WIN_VIDEOS = [
    "https://files.catbox.moe/5cezg5.mp4",
    "https://files.catbox.moe/dw2df7.mp4",
    "https://files.catbox.moe/5vgulb.mp4",
]

LOSE_VIDEOS = [
    "https://files.catbox.moe/ucdvpd.mp4",
    "https://files.catbox.moe/bhwnu4.mp4",
]

ATTACK_MOVES = [
    ("Sword Slash", 10, 25),
    ("Fireball", 12, 28),
    ("Arrow Shot", 8, 22),
    ("Heavy Punch", 10, 26),
    ("Lightning Strike", 11, 30),
]

# ====== state ======
active_battles: Dict[int, bool] = {}       # user_id -> True when in battle
battle_tasks: Dict[str, asyncio.Task] = {}  # key: "challenger:opponent" -> Task


# ====== helpers ======
def hp_bar(hp: int) -> str:
    filled = max(0, min(10, int(hp / 10)))
    return "▰" * filled + "▱" * (10 - filled)


async def ensure_user(uid: int, name: str) -> None:
    """Ensure user exists in DB with default values."""
    if not await user_collection.find_one({"id": uid}):
        await user_collection.insert_one({
            "id": uid,
            "first_name": name,
            "balance": 1000,
            "wins": 0,
            "losses": 0
        })


def battle_key(challenger: int, opponent: int) -> str:
    return f"{min(challenger, opponent)}:{max(challenger, opponent)}"


# ====== /battle command ======
@app.on_message(filters.command("battle"))
async def battle_cmd(client, message: Message):
    if not message.reply_to_message:
        return await message.reply("Reply to someone to challenge them! Usage: reply + /battle <amount>")
        
    opponent = message.reply_to_message.from_user
    user = message.from_user

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("Usage: /battle <amount>` (reply to a user)")

    bet = int(parts[1])
    if bet <= 0:
        return await message.reply("Bet must be greater than 0.")

    if opponent.id == user.id:
        return await message.reply("You cannot battle yourself.")

    await ensure_user(user.id, user.first_name)
    await ensure_user(opponent.id, opponent.first_name)

    udata = await user_collection.find_one({"id": user.id})
    odata = await user_collection.find_one({"id": opponent.id})

    if udata["balance"] < bet:
        return await message.reply("You don’t have enough balance.")
    if odata["balance"] < bet:
        return await message.reply(f"{opponent.first_name} doesn’t have enough balance.")

    if user.id in active_battles or opponent.id in active_battles:
        return await message.reply("Either you or the opponent is already in a battle.")

    # short safe callback data (keep < 64 chars)
    cb_accept = f"by|{user.id}|{opponent.id}|{bet}"
    cb_reject = f"bn|{user.id}|{opponent.id}"

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Accept ⚔️", callback_data=cb_accept),
                InlineKeyboardButton("Reject ❌", callback_data=cb_reject),
            ]
        ]
    )

    await message.reply(
        f"{user.mention} challenged {opponent.mention} for **{bet}** coins!\n\n"
        "Opponent: reply with Accept or Reject.",
        reply_markup=buttons
    )


# ====== accept handler ======
@app.on_callback_query(filters.regex(r"^by\|"))
async def accept_battle(client, cq: CallbackQuery):
    # answer immediately to remove spinner
    await cq.answer()

    # parse
    try:
        _, c_s, o_s, bet_s = cq.data.split("|")
        challenger = int(c_s)
        opponent = int(o_s)
        bet = int(bet_s)
    except Exception:
        return await cq.answer("Invalid callback data.", show_alert=True)

    # only the opponent can accept
    if cq.from_user.id != opponent:
        return await cq.answer("This challenge is not for you.", show_alert=True)

    # double check balances & concurrent state
    await ensure_user(challenger, "Challenger")
    await ensure_user(opponent, "Opponent")
    cdata = await user_collection.find_one({"id": challenger})
    odata = await user_collection.find_one({"id": opponent})

    if cdata["balance"] < bet or odata["balance"] < bet:
        return await cq.edit_message_text("One of the players does not have enough balance anymore.")

    if challenger in active_battles or opponent in active_battles:
        return await cq.edit_message_text("Someone is already in another battle.")

    # mark active
    active_battles[challenger] = True
    active_battles[opponent] = True

    # debit immediately to prevent race conditions
    await user_collection.update_one({"id": challenger}, {"$inc": {"balance": -bet}})
    await user_collection.update_one({"id": opponent}, {"$inc": {"balance": -bet}})

    # start battle message
    try:
        await cq.edit_message_text("Battle accepted! Preparing the arena... ⚔️")
    except:
        # safe fallback
        pass

    msg = await cq.message.reply_photo(
        random.choice(BATTLE_IMAGES),
        caption=f"⚔️ Battle Started!\n{cdata['first_name']} vs {odata['first_name']}\nBet: **{bet}**"
    )

    # create and track task
    key = battle_key(challenger, opponent)
    task = asyncio.create_task(run_battle(msg, challenger, opponent, bet, cdata, odata))
    # add safe done callback so Python doesn't warn on loop close
    task.add_done_callback(lambda t: t.exception() if t.done() and t.exception() else None)
    battle_tasks[key] = task


# ====== reject handler ======
@app.on_callback_query(filters.regex(r"^bn\|"))
async def reject_battle(client, cq: CallbackQuery):
    # answer quickly to remove spinner
    await cq.answer()

    try:
        _, c_s, o_s = cq.data.split("|")
        challenger = int(c_s)
        opponent = int(o_s)
    except Exception:
        return await cq.answer("Invalid callback data.", show_alert=True)

    # allow either challenger or opponent to trigger reject (safer UX)
    if cq.from_user.id not in [challenger, opponent]:
        return await cq.answer("This isn't your battle.", show_alert=True)

    # edit message to show rejection
    try:
        await cq.edit_message_text("❌ The challenge was rejected.")
    except:
        try:
            await cq.message.reply_text("❌ The challenge was rejected.")
        except:
            pass


# ====== main battle loop ======
async def run_battle(msg: Message, challenger: int, opponent: int, bet: int, cdata: dict, odata: dict):
    key = battle_key(challenger, opponent)
    hpC = 100
    hpO = 100
    turn = 0

    try:
        while hpC > 0 and hpO > 0:
            await asyncio.sleep(1)  # pacing; increase to slow down
            turn += 1

            attacker = random.choice(["c", "o"])
            move = random.choice(ATTACK_MOVES)
            dmg = random.randint(move[1], move[2])

            if attacker == "c":
                hpO -= dmg
                txt = f"{cdata['first_name']} used {move[0]} → {dmg} dmg!"
            else:
                hpC -= dmg
                txt = f"{odata['first_name']} used {move[0]} → {dmg} dmg!"

            hpC = max(0, hpC)
            hpO = max(0, hpO)

            # update caption; fail silently if Telegram blocks edits
            caption = (
                f"**Turn {turn}**\n{txt}\n\n"
                f"{cdata['first_name']} HP: {hpC} {hp_bar(hpC)}\n"
                f"{odata['first_name']} HP: {hpO} {hp_bar(hpO)}"
            )
            try:
                await msg.edit_caption(caption)
            except:
                # maybe message was converted to text earlier; try edit_text
                try:
                    await msg.edit_text(caption)
                except:
                    pass

        # determine winner
        winner = challenger if hpC > 0 else opponent
        loser = opponent if hpC > 0 else challenger

        # update DB
        await user_collection.update_one({"id": winner}, {"$inc": {"balance": bet * 2, "wins": 1}})
        await user_collection.update_one({"id": loser}, {"$inc": {"losses": 1}})

        wname = (await user_collection.find_one({"id": winner}))["first_name"]
        lname = (await user_collection.find_one({"id": loser}))["first_name"]

        try:
            await msg.reply_video(random.choice(WIN_VIDEOS), caption=f"🏆 {wname} won the battle!")
            await msg.reply_video(random.choice(LOSE_VIDEOS), caption=f"💀 {lname} lost the battle!")
        except:
            # if videos fail, send simple text result
            await msg.reply_text(f"🏆 {wname} won the battle! {lname} lost.")

    except asyncio.CancelledError:
        # if task cancelled, refund both players fairly (optional)
        try:
            await user_collection.update_one({"id": challenger}, {"$inc": {"balance": bet}})
            await user_collection.update_one({"id": opponent}, {"$inc": {"balance": bet}})
        except:
            pass
    except Exception as exc:
        # log exception somewhere if you have logger; keep safe behaviour
        try:
            await msg.reply_text("⚠️ Battle ended unexpectedly.")
        except:
            pass
    finally:
        # cleanup
        active_battles.pop(challenger, None)
        active_battles.pop(opponent, None)
        # remove task from registry
        battle_tasks.pop(key, None)


# ====== optional cleanup helper (call on graceful shutdown) ======
async def cancel_all_battles():
    """If you want to cancel all running battle tasks on shutdown, call this."""
    for k, t in list(battle_tasks.items()):
        if not t.done():
            t.cancel()
    # wait a bit for cancellations
    await asyncio.sleep(0.1)
