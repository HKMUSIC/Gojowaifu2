import random
import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import app, user_collection


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

active_battles = {}


def hp_bar(hp: int):
    filled = int(hp / 10)
    return "▰" * filled + "▱" * (10 - filled)


async def ensure_user(uid, name):
    if not await user_collection.find_one({"id": uid}):
        await user_collection.insert_one({
            "id": uid,
            "first_name": name,
            "balance": 1000,
            "wins": 0,
            "losses": 0
        })


# ============================== #
#       BATTLE COMMAND
# ============================== #

@app.on_message(filters.command("battle"))
async def battle_cmd(client, message):

    if not message.reply_to_message:
        return await message.reply("Reply to someone to challenge them!")

    opponent = message.reply_to_message.from_user
    user = message.from_user

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("Usage: Reply to a user → `/battle amount`")

    bet = int(parts[1])

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
        return await message.reply("Someone is already in a battle!")

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Accept", callback_data=f"battle_yes:{user.id}:{opponent.id}:{bet}"),
                InlineKeyboardButton("Reject", callback_data=f"battle_no:{user.id}:{opponent.id}"),
            ]
        ]
    )

    await message.reply(
        f"{user.mention} challenged {opponent.mention} for {bet} coins!",
        reply_markup=buttons
    )


# ============================== #
#       ACCEPT BATTLE
# ============================== #

@app.on_callback_query(filters.regex("^battle_yes"))
async def accept_battle(client, cq):

    _, c_s, o_s, bet_s = cq.data.split(":")
    challenger = int(c_s)
    opponent = int(o_s)
    bet = int(bet_s)

    if cq.from_user.id != opponent:
        return await cq.answer("Not for you.", show_alert=True)

    active_battles[challenger] = True
    active_battles[opponent] = True

    await user_collection.update_one({"id": challenger}, {"$inc": {"balance": -bet}})
    await user_collection.update_one({"id": opponent}, {"$inc": {"balance": -bet}})

    cdata = await user_collection.find_one({"id": challenger})
    odata = await user_collection.find_one({"id": opponent})

    msg = await cq.message.reply_photo(
        random.choice(BATTLE_IMAGES),
        caption=f"Battle Started!\n{cdata['first_name']} vs {odata['first_name']}\nBet: {bet}"
    )

    # Safe task creation
    task = asyncio.create_task(
        run_battle(msg, challenger, opponent, bet, cdata, odata)
    )
    task.add_done_callback(lambda t: None)   # prevents "task destroyed" error


# ============================== #
#       MAIN BATTLE LOOP
# ============================== #

async def run_battle(msg, challenger, opponent, bet, cdata, odata):

    hpC = 100
    hpO = 100
    turn = 0

    try:
        while hpC > 0 and hpO > 0:
            await asyncio.sleep(1)
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

            try:
                await msg.edit_caption(
                    f"Turn {turn}\n{txt}\n\n"
                    f"{cdata['first_name']} HP: {hpC} {hp_bar(hpC)}\n"
                    f"{odata['first_name']} HP: {hpO} {hp_bar(hpO)}"
                )
            except:
                pass

        winner = challenger if hpC > 0 else opponent
        loser = opponent if hpC > 0 else challenger

        await user_collection.update_one({"id": winner}, {"$inc": {"balance": bet * 2, "wins": 1}})
        await user_collection.update_one({"id": loser}, {"$inc": {"losses": 1}})

        wname = (await user_collection.find_one({"id": winner}))["first_name"]
        lname = (await user_collection.find_one({"id": loser}))["first_name"]

        await msg.reply_video(random.choice(WIN_VIDEOS), caption=f"{wname} won the battle!")
        await msg.reply_video(random.choice(LOSE_VIDEOS), caption=f"{lname} lost!")

    except asyncio.CancelledError:
        print("Battle task cancelled safely")

    finally:
        active_battles.pop(challenger, None)
        active_battles.pop(opponent, None)


# ============================== #
#       REJECT BATTLE
# ============================== #

@app.on_callback_query(filters.regex("^battle_no"))
async def reject_battle(client, cq):

    _, c_s, o_s = cq.data.split(":")

    if cq.from_user.id not in [int(c_s), int(o_s)]:
        return await cq.answer("Not for you.", show_alert=True)

    await cq.message.edit("Battle rejected.")
