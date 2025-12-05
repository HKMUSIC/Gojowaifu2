import random
import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import app, user_collection


BATTLE_IMAGES = [
    "https://files.catbox.moe/1f6a2q.jpg",
    "https://files.catbox.moe/0o7nkl.jpg",
    "https://files.catbox.moe/3gljwk.jpg",
    "https://files.catbox.moe/5dtj1p.jpg"
]

WIN_VIDEOS = [
    "https://files.catbox.moe/5cezg5.mp4",
    "https://files.catbox.moe/dw2df7.mp4",
    "https://files.catbox.moe/5vgulb.mp4"
]

LOSE_VIDEOS = [
    "https://files.catbox.moe/ucdvpd.mp4",
    "https://files.catbox.moe/bhwnu4.mp4"
]

ATTACK_MOVES = [
    ("⚔️ Sword Slash", 10, 25),
    ("🔥 Fireball", 12, 28),
    ("🏹 Arrow Shot", 8, 22),
    ("👊 Heavy Punch", 10, 26),
    ("⚡ Lightning Strike", 11, 30),
]

active_battles = {}


def hp_bar(hp):
    seg = 10
    f = int((hp / 100) * seg)
    return "▰" * f + "▱" * (seg - f)


async def ensure_user(uid, name):
    user = await user_collection.find_one({"id": uid})
    if not user:
        await user_collection.insert_one({
            "id": uid,
            "first_name": name,
            "balance": 1000,
            "wins": 0,
            "losses": 0
        })


@app.on_message(filters.command("battle"))
async def battle_cmd(client, message):

    parts = message.text.split()

    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("⚔️ Reply or Tag user:\n`/battle <amount>`")

    bet_amount = int(parts[1])

    if bet_amount <= 0:
        return await message.reply("❌ Bet must be a positive number.")

    opponent = None

    if message.reply_to_message:
        opponent = message.reply_to_message.from_user
    else:
        if message.entities:
            for ent in message.entities:
                if ent.type == "text_mention":
                    opponent = ent.user
                    break
                if ent.type == "mention":
                    username = message.text[ent.offset: ent.offset + ent.length]
                    opponent = await client.get_users(username)
                    break

    if not opponent:
        return await message.reply("❌ Tag or reply to a user.")

    user = message.from_user

    if opponent.id == user.id:
        return await message.reply("😂 You can't battle yourself.")

    await ensure_user(user.id, user.first_name)
    await ensure_user(opponent.id, opponent.first_name)

    user_data = await user_collection.find_one({"id": user.id})
    opp_data = await user_collection.find_one({"id": opponent.id})

    if user_data["balance"] < bet_amount:
        return await message.reply("❌ You don't have enough balance.")

    if opp_data["balance"] < bet_amount:
        return await message.reply(f"❌ {opponent.first_name} doesn't have enough balance.")

    if user.id in active_battles or opponent.id in active_battles:
        return await message.reply("⛔ One of you is already in a battle.")

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"battle_accept:{user.id}:{opponent.id}:{bet_amount}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"battle_reject:{user.id}:{opponent.id}")
        ]
    ])

    await message.reply(
        f"⚔️ **{user.first_name}** challenged **{opponent.first_name}** for **{bet_amount} coins**!",
        reply_markup=keyboard
    )


@app.on_callback_query(filters.regex("battle_accept"))
async def battle_accept(client, cq):

    _, challenger, opponent, bet = cq.data.split(":")
    challenger = int(challenger)
    opponent = int(opponent)
    bet = int(bet)

    if cq.from_user.id != opponent:
        return await cq.answer("Not for you!", show_alert=True)

    active_battles[challenger] = True
    active_battles[opponent] = True

    await user_collection.update_one({"id": challenger}, {"$inc": {"balance": -bet}})
    await user_collection.update_one({"id": opponent}, {"$inc": {"balance": -bet}})

    cdata = await user_collection.find_one({"id": challenger})
    odata = await user_collection.find_one({"id": opponent})

    hpC = 100
    hpO = 100
    turn = 0

    msg = await cq.message.reply_photo(
        random.choice(BATTLE_IMAGES),
        caption=f"⚔️ Battle Started!\n{cdata['first_name']} vs {odata['first_name']}\nPot: {bet * 2}"
    )

    while hpC > 0 and hpO > 0:
        await asyncio.sleep(1)
        turn += 1
        attacker = random.choice(["c", "o"])
        move = random.choice(ATTACK_MOVES)
        dmg = random.randint(move[1], move[2])

        if attacker == "c":
            hpO -= dmg
            if hpO < 0: hpO = 0
            text = f"{cdata['first_name']} used {move[0]} (-{dmg})"
        else:
            hpC -= dmg
            if hpC < 0: hpC = 0
            text = f"{odata['first_name']} used {move[0]} (-{dmg})"

        await msg.edit_caption(
            f"⚔️ Turn {turn}\n{text}\n\n"
            f"{cdata['first_name']}: {hpC} {hp_bar(hpC)}\n"
            f"{odata['first_name']}: {hpO} {hp_bar(hpO)}"
        )

    if hpC > 0:
        winner = challenger
        loser = opponent
        wname = cdata["first_name"]
        lname = odata["first_name"]
    else:
        winner = opponent
        loser = challenger
        wname = odata["first_name"]
        lname = cdata["first_name"]

    pot = bet * 2

    await user_collection.update_one({"id": winner}, {"$inc": {"balance": pot, "wins": 1}})
    await user_collection.update_one({"id": loser}, {"$inc": {"losses": 1}})

    await cq.message.reply_video(random.choice(WIN_VIDEOS), caption=f"🏆 {wname} WON +{pot}!")
    await cq.message.reply_video(random.choice(LOSE_VIDEOS), caption=f"💀 {lname} LOST")

    active_battles.pop(challenger, None)
    active_battles.pop(opponent, None)


@app.on_callback_query(filters.regex("battle_reject"))
async def battle_reject(client, cq):
    await cq.message.edit("❌ Challenge Rejected.")
