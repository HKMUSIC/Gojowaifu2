import random
import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import app, user_collection

# Assets
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
    ("Sword Slash", 10, 25),
    ("Fireball", 12, 28),
    ("Arrow Shot", 8, 22),
    ("Heavy Punch", 10, 26),
    ("Lightning Strike", 11, 30),
]

active_battles = {}


def hp_bar(hp: int) -> str:
    seg = 10
    filled = max(0, min(seg, int((hp / 100) * seg)))
    return "▰" * filled + "▱" * (seg - filled)


async def ensure_user(uid: int, name: str):
    doc = await user_collection.find_one({"id": uid})
    if not doc:
        await user_collection.insert_one({
            "id": uid,
            "first_name": name or "User",
            "balance": 1000,
            "wins": 0,
            "losses": 0
        })


# /battle command: reply to a user's message OR tag them in the message
@app.on_message(filters.command("battle"))
async def battle_cmd(client, message):
    parts = message.text.split()

    if len(parts) != 2 or not parts[1].isdigit():
        # plain text message, no code formatting or angle brackets
        return await message.reply("Usage: reply to a user or tag them, then send: /battle <amount>")

    bet_amount = int(parts[1])
    if bet_amount <= 0:
        return await message.reply("Bet amount must be a positive integer.")

    # find opponent: prefer reply, else mention/text_mention
    opponent = None
    if message.reply_to_message:
        opponent = message.reply_to_message.from_user
    else:
        if message.entities:
            for ent in message.entities:
                # text_mention contains the user object
                if ent.type == "text_mention":
                    opponent = ent.user
                    break
                if ent.type == "mention":
                    # extract username string (like @username)
                    username = message.text[ent.offset: ent.offset + ent.length]
                    try:
                        opponent = await client.get_users(username)
                        break
                    except Exception:
                        opponent = None

    if not opponent:
        return await message.reply("Please reply to or tag the user you want to challenge.")

    user = message.from_user
    if opponent.id == user.id:
        return await message.reply("You cannot challenge yourself.")

    # ensure DB entries
    await ensure_user(user.id, user.first_name)
    await ensure_user(opponent.id, opponent.first_name)

    user_doc = await user_collection.find_one({"id": user.id})
    opp_doc = await user_collection.find_one({"id": opponent.id})

    if not user_doc or not opp_doc:
        return await message.reply("Database error. Try again later.")

    if user_doc.get("balance", 0) < bet_amount:
        return await message.reply("You do not have enough balance for that bet.")

    if opp_doc.get("balance", 0) < bet_amount:
        return await message.reply(f"{opponent.first_name} does not have enough balance for that bet.")

    if user.id in active_battles or opponent.id in active_battles:
        return await message.reply("Either you or the opponent is already in a battle.")

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Accept", callback_data=f"battle_accept:{user.id}:{opponent.id}:{bet_amount}"),
            InlineKeyboardButton("Reject", callback_data=f"battle_reject:{user.id}:{opponent.id}")
        ]
    ])

    # plain text reply to avoid entity parsing problems
    await message.reply(f"{user.first_name} has challenged {opponent.first_name} for {bet_amount} coins. {opponent.first_name}, do you accept?", reply_markup=keyboard)


@app.on_callback_query(filters.regex(r"^battle_accept"))
async def battle_accept(client, cq):
    try:
        _, challenger_s, opponent_s, bet_s = cq.data.split(":")
        challenger = int(challenger_s)
        opponent = int(opponent_s)
        bet = int(bet_s)
    except Exception:
        return await cq.answer("Invalid data.", show_alert=True)

    if cq.from_user.id != opponent:
        return await cq.answer("Only the challenged user can accept.", show_alert=True)

    # lock players
    active_battles[challenger] = True
    active_battles[opponent] = True

    # deduct bet safely
    await user_collection.update_one({"id": challenger}, {"$inc": {"balance": -bet}})
    await user_collection.update_one({"id": opponent}, {"$inc": {"balance": -bet}})

    cdata = await user_collection.find_one({"id": challenger})
    odata = await user_collection.find_one({"id": opponent})

    hpC = 100
    hpO = 100
    turn = 0

    # send initial photo (plain caption)
    msg = await cq.message.reply_photo(random.choice(BATTLE_IMAGES), caption=f"Battle started: {cdata['first_name']} vs {odata['first_name']}. Pot: {bet * 2}")

    while hpC > 0 and hpO > 0:
        await asyncio.sleep(1)
        turn += 1

        attacker = random.choice(["c", "o"])
        move = random.choice(ATTACK_MOVES)
        dmg = random.randint(move[1], move[2])

        if attacker == "c":
            hpO = max(0, hpO - dmg)
            action_text = f"{cdata['first_name']} used {move[0]} and did {dmg} damage"
        else:
            hpC = max(0, hpC - dmg)
            action_text = f"{odata['first_name']} used {move[0]} and did {dmg} damage"

        # edit caption (plain text)
        try:
            await msg.edit_caption(
                f"Turn {turn}\n{action_text}\n\n"
                f"{cdata['first_name']}: {hpC} {hp_bar(hpC)}\n"
                f"{odata['first_name']}: {hpO} {hp_bar(hpO)}"
            )
        except Exception:
            # if edit fails, ignore and continue loop
            pass

    # determine winner
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

    # send small videos; plain captions
    try:
        await cq.message.reply_video(random.choice(WIN_VIDEOS), caption=f"{wname} wins and gains {pot} coins")
    except Exception:
        pass
    try:
        await cq.message.reply_video(random.choice(LOSE_VIDEOS), caption=f"{lname} lost the battle")
    except Exception:
        pass

    # unlock
    active_battles.pop(challenger, None)
    active_battles.pop(opponent, None)


@app.on_callback_query(filters.regex(r"^battle_reject"))
async def battle_reject(client, cq):
    try:
        await cq.message.edit("Battle rejected.")
    except Exception:
        try:
            await cq.answer("Battle rejected.", show_alert=True)
        except Exception:
            pass
