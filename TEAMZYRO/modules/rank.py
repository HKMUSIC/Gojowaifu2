from TEAMZYRO import app   # <<< REQUIRED
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import html
import random

from TEAMZYRO import user_collection, top_global_groups_collection

PHOTO_URL = ["https://files.catbox.moe/9j8e6b.jpg"]


# ---------- Badges ----------
def get_badge(rank: int, total: int):
    if total <= 0:
        return "", ""
    if rank == 1:
        return "🥇", "Champion"
    if rank == 2:
        return "🥈", "2nd Place"
    if rank == 3:
        return "🥉", "3rd Place"
    if rank <= 10:
        return "🏅", f"Top {rank}"

    pct = rank / total
    if pct <= 0.01:
        return "💎", "Top 1%"
    if pct <= 0.05:
        return "🔷", "Top 5%"
    if pct <= 0.10:
        return "🔹", "Top 10%"
    return "", ""


# ---------- Build captions ----------
def build_user_leaderboard(data):
    total = len(data)
    caption = "<b>🏆 TOP 10 USERS (CHARACTERS)</b>\n\n"
    for i, user in enumerate(data, start=1):
        uid = user.get("id")
        name = html.escape(user.get("first_name", "Unknown"))
        if len(name) > 15:
            name = name[:15] + "..."
        count = len(user.get("characters", []))
        badge, _ = get_badge(i, total)
        caption += f"{i}. {badge} <a href='tg://user?id={uid}'><b>{name}</b></a> ➜ <b>{count}</b>\n"
    return caption


def build_group_leaderboard(data):
    caption = "<b>🏆 TOP 10 GROUPS</b>\n\n"
    for i, group in enumerate(data, start=1):
        name = html.escape(group.get("group_name", "Unknown"))
        if len(name) > 15:
            name = name[:15] + "..."
        count = group.get("count", 0)
        badge, _ = get_badge(i, len(data))
        caption += f"{i}. {badge} <b>{name}</b> ➜ <b>{count}</b>\n"
    return caption


def build_coin_leaderboard(data):
    caption = "<b>🏆 TOP 10 RICHEST USERS</b>\n\n"
    total = len(data)
    for i, user in enumerate(data, start=1):
        uid = user.get("id")
        name = html.escape(user.get("first_name", "Unknown"))
        if len(name) > 15:
            name = name[:15] + "..."
        coins = user.get("balance", 0)
        badge, _ = get_badge(i, total)
        caption += f"{i}. {badge} <a href='tg://user?id={uid}'><b>{name}</b></a> ➜ <b>{coins}</b>\n"
    return caption


# ---------- Buttons ----------
def get_buttons(active):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Users" if active == "top" else "Users", callback_data="top"),
            InlineKeyboardButton("👥 Groups" if active == "top_group" else "Groups", callback_data="top_group"),
        ],
        [
            InlineKeyboardButton("💰 Richest" if active == "mtop" else "Richest", callback_data="mtop")
        ]
    ])


# ---------- /rank ----------
@app.on_message(filters.command("rank"))
async def rank_cmd(client, message):
    cursor = user_collection.find({}, {"_id": 0, "id": 1, "first_name": 1, "characters": 1})
    data = await cursor.to_list(length=None)
    data.sort(key=lambda x: len(x.get("characters", [])), reverse=True)
    top_users = data[:10]

    caption = build_user_leaderboard(top_users)

    await message.reply_photo(
        photo=random.choice(PHOTO_URL),
        caption=caption,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=get_buttons("top")
    )


# ---------- BUTTON HANDLERS ----------
@app.on_callback_query(filters.regex("^(top|top_group|mtop)$"))
async def leaderboard_buttons(client, query):
    btn = query.data

    if btn == "top":
        cursor = user_collection.find({}, {"_id":0,"id":1,"first_name":1,"characters":1})
        data = await cursor.to_list(length=None)
        data.sort(key=lambda x: len(x.get("characters", [])), reverse=True)
        caption = build_user_leaderboard(data[:10])

    elif btn == "top_group":
        cursor = top_global_groups_collection.aggregate([
            {"$project": {"group_name":1, "count":1}},
            {"$sort":{"count":-1}},
            {"$limit":10}
        ])
        data = await cursor.to_list(length=10)
        caption = build_group_leaderboard(data)

    else:  # richest
        cursor = user_collection.find({}, {"_id":0,"id":1,"first_name":1,"balance":1})
        data = await cursor.to_list(length=None)
        data.sort(key=lambda x: x.get("balance", 0), reverse=True)
        caption = build_coin_leaderboard(data[:10])

    await query.message.edit_caption(
        caption,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=get_buttons(btn)
    )
    await query.answer()


# ---------- /profile ----------
@app.on_message(filters.command("profile"))
async def profile_cmd(client, message):
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        parts = message.text.split()
        if len(parts) >= 2:
            try:
                t = parts[1]
                if t.startswith("@"):
                    target = await client.get_users(t)
                else:
                    target = await client.get_users(int(t))
            except:
                return await message.reply_text("Invalid user.")

    if not target:
        target = message.from_user

    uid = target.id
    user_doc = await user_collection.find_one({"id": uid})
    if not user_doc:
        return await message.reply_text("User not found in DB.")

    cursor = user_collection.find({}, {"_id":0,"id":1,"characters":1})
    all_users = await cursor.to_list(length=None)
    all_users.sort(key=lambda x: len(x.get("characters", [])), reverse=True)

    total_users = len(all_users)
    rank = next((i for i, u in enumerate(all_users, start=1) if u["id"] == uid), 0)

    badge_emoji, badge_label = get_badge(rank, total_users)

    chars = len(user_doc.get("characters", []))
    balance = user_doc.get("balance", 0)

    caption = (
        f"<b>{html.escape(target.first_name)}</b> {badge_emoji}\n"
        f"{badge_label}\n\n"
        f"🧾 Characters: <b>{chars}</b>\n"
        f"💰 Balance: <b>{balance}</b>\n"
        f"🏅 Rank: <b>#{rank} / {total_users}</b>"
    )

    try:
        photos = await client.get_profile_photos(uid, limit=1)
        if photos.total_count > 0:
            return await message.reply_photo(
                photos.photos[0].file_id,
                caption=caption,
                parse_mode=enums.ParseMode.HTML
            )
    except:
        pass

    await message.reply_text(caption, parse_mode=enums.ParseMode.HTML)
