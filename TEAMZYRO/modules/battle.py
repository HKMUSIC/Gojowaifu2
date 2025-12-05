import random
import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import ZYRO, user_collection

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

CRITICAL_CHANCE = 12
active_battles = {}

def hp_bar(hp):
    seg = 10
    f = int((hp / 100) * seg)
    return "▰" * f + "▱" * (seg - f)


async def ensure_user(uid, name):
    if not await user_collection.find_one({"id": uid}):
        await user_collection.insert_one({
            "id": uid,
            "first_name": name,
            "balance": 1000,
            "wins": 0,
            "losses": 0
        })


@ZYRO.on_message(filters.command("battle"))
async def battle_cmd(client, message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    args = message.text.split()

    # Bet amount required
    if len(args) != 2 or not args[1].isdigit():
        return await message.reply(
            "⚔️ 𝗨𝗦𝗔𝗚𝗘:\nReply to user:\n`/battle <amount>`\n\nExample:\nReply to a user → `/battle 500`",
            quote=True
        )

    bet_amount = int(args[1])

    if bet_amount <= 0:
        return await message.reply("❌ Bet must be positive!")

    # --- opponent detection ---
    opponent = None

    # 1) If replying to a message
    if message.reply_to_message:
        opponent = message.reply_to_message.from_user

    # 2) If user is tagged in the message
    else:
        if message.entities:
            for entity in message.entities:
                if entity.type == "mention" or entity.type == "text_mention":
                    if entity.type == "text_mention":
                        opponent = entity.user
                    else:
                        username = message.text[entity.offset: entity.offset + entity.length]
                        opponent = await client.get_users(username)
                    break

    if not opponent:
        return await message.reply("❌ Tag or reply to the user you want to battle.", quote=True)

    opponent_id = opponent.id
    opponent_name = opponent.first_name

    if opponent_id == user_id:
        return await message.reply("😂 You can't battle yourself!")

    # Ensure DB user setup
    await ensure_user(user_id, user_name)
    await ensure_user(opponent_id, opponent_name)

    user_data = await user_collection.find_one({"id": user_id})
    opponent_data = await user_collection.find_one({"id": opponent_id})

    if user_data["balance"] < bet_amount:
        return await message.reply("❌ You don't have enough balance!")

    if opponent_data["balance"] < bet_amount:
        return await message.reply(f"❌ {opponent_name} doesn't have enough balance!")

    # Already in battle?
    if user_id in active_battles or opponent_id in active_battles:
        return await message.reply("⛔ Either you or opponent is already in a battle!")

    # Challenge buttons
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Accept",
                                 callback_data=f"battle_accept:{user_id}:{opponent_id}:{bet_amount}"),
            InlineKeyboardButton("❌ Reject",
                                 callback_data=f"battle_reject:{user_id}:{opponent_id}")
        ]]
    )

    await message.reply(
        f"⚔️ <b>{user_name}</b> has challenged <b>{opponent_name}</b> for <b>{bet_amount} coins</b>!\n\n"
        f"{opponent_name}, do you accept?",
        parse_mode="html",
        reply_markup=keyboard
    )


@ZYRO.on_callback_query(filters.regex("battle_accept"))
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

    hpC = hpO = 100
    turn = 0

    msg = await cq.message.reply_photo(
        random.choice(BATTLE_IMAGES),
        caption=f"⚔️ Battle Started!\n{cdata['first_name']} vs {odata['first_name']}\nPot: {bet * 2} coins"
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
            text = f"{cdata['first_name']} used {move[0]} for {dmg}"
        else:
            hpC -= dmg
            if hpC < 0: hpC = 0
            text = f"{odata['first_name']} used {move[0]} for {dmg}"

        await msg.edit_caption(
            f"⚔️ Turn {turn}\n{text}\n\n"
            f"{cdata['first_name']}: {hpC} {hp_bar(hpC)}\n"
            f"{odata['first_name']}: {hpO} {hp_bar(hpO)}"
        )

    if hpC > 0:
        winner, loser = challenger, opponent
        wname, lname = cdata['first_name'], odata['first_name']
    else:
        winner, loser = opponent, challenger
        wname, lname = odata['first_name'], cdata['first_name']

    pot = bet * 2

    await user_collection.update_one({"id": winner}, {"$inc": {"balance": pot, "wins": 1}})
    await user_collection.update_one({"id": loser}, {"$inc": {"losses": 1}})

    await cq.message.reply_video(random.choice(WIN_VIDEOS), caption=f"🏆 {wname} WON +{pot}")
    await cq.message.reply_video(random.choice(LOSE_VIDEOS), caption=f"💀 {lname} LOST")

    active_battles.pop(challenger, None)
    active_battles.pop(opponent, None)


@ZYRO.on_callback_query(filters.regex("battle_reject"))
async def battle_reject(client, cq):
    await cq.message.edit("❌ Challenge Rejected.")
