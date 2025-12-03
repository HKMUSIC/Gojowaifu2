import asyncio
import html
import random
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# reuse your imports/collections: app, user_collection, top_global_groups_collection
# PHOTO_URL remains same
PHOTO_URL = ["https://files.catbox.moe/9j8e6b.jpg"]

# ---------- Badges ----------
def get_badge(rank: int, total: int):
    """Return (emoji, label) based on rank and total players."""
    if total <= 0:
        return "", ""

    # absolute positions
    if rank == 1:
        return "🥇", "Champion"
    if rank == 2:
        return "🥈", "2nd Place"
    if rank == 3:
        return "🥉", "3rd Place"
    if rank <= 10:
        return "🏅", f"Top {rank}"
    # percentile-based badges
    pct = rank / total
    if pct <= 0.01:
        return "💎", "Top 1%"
    if pct <= 0.05:
        return "🔷", "Top 5%"
    if pct <= 0.10:
        return "🔹", "Top 10%"
    return "", ""

# ---------- Modified build functions to include badges ----------
def build_user_leaderboard_with_badges(data, include_badge=True):
    """data is list of dicts sorted by characters descending"""
    total = len(data)
    caption = "<b>🏆 TOP 10 USERS (CHARACTERS)</b>\n\n"
    for i, user in enumerate(data, start=1):
        uid = user.get("id", 0)
        name = html.escape(user.get("first_name", "Unknown"))
        if len(name) > 15:
            name = name[:15] + "..."
        count = len(user.get("characters", []))
        badge_emoji, _ = (get_badge(i, total) if include_badge else ("", ""))
        caption += f"{i}. {badge_emoji} <a href='tg://user?id={uid}'><b>{name}</b></a> ➜ <b>{count}</b>\n"
    return caption

def build_group_leaderboard_with_badges(data):
    caption = "<b>🏆 TOP 10 GROUPS</b>\n\n"
    total = sum(g.get("count", 0) for g in data) or len(data)
    for i, group in enumerate(data, start=1):
        name = html.escape(group.get("group_name", "Unknown"))
        if len(name) > 15:
            name = name[:15] + "..."
        count = group.get("count", 0)
        badge_emoji, _ = get_badge(i, len(data))
        caption += f"{i}. {badge_emoji} <b>{name}</b> ➜ <b>{count}</b>\n"
    return caption

def build_coin_leaderboard_with_badges(data):
    caption = "<b>🏆 TOP 10 RICHEST USERS</b>\n\n"
    total = len(data)
    for i, user in enumerate(data, start=1):
        uid = user.get("id", 0)
        name = html.escape(user.get("first_name", "Unknown"))
        if len(name) > 15:
            name = name[:15] + "..."
        coins = user.get("balance", 0)  # ensure you use 'balance'
        badge_emoji, _ = get_badge(i, total)
        caption += f"{i}. {badge_emoji} <a href='tg://user?id={uid}'><b>{name}</b></a> ➜ <b>{coins}</b>\n"
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

# ---------- Animated leaderboard helper ----------
async def animate_leaderboard(message_obj, cycles=3, delay=2.0):
    """
    message_obj is the sent Message object (the one with photo/caption).
    cycles: how many full cycles to run (Users->Groups->Richest). Each view shown for `delay` seconds.
    """
    try:
        for _ in range(cycles):
            # Users
            cursor = user_collection.find({}, {"_id":0,"id":1,"first_name":1,"characters":1})
            udata = await cursor.to_list(length=None)
            udata.sort(key=lambda x: len(x.get("characters", [])), reverse=True)
            top_users = udata[:10]
            caption = build_user_leaderboard_with_badges(top_users)
            try:
                await message_obj.edit_caption(caption, parse_mode=enums.ParseMode.HTML, reply_markup=get_buttons("top"))
            except:
                # fallback to edit_message_text if caption edit fails
                try:
                    await message_obj.edit_text(caption, parse_mode=enums.ParseMode.HTML)
                except:
                    pass
            await asyncio.sleep(delay)

            # Groups
            gcursor = top_global_groups_collection.aggregate([
                {"$project": {"group_name":1, "count":1}},
                {"$sort":{"count":-1}},
                {"$limit":10}
            ])
            gdata = await gcursor.to_list(length=10)
            caption = build_group_leaderboard_with_badges(gdata)
            try:
                await message_obj.edit_caption(caption, parse_mode=enums.ParseMode.HTML, reply_markup=get_buttons("top_group"))
            except:
                try:
                    await message_obj.edit_text(caption, parse_mode=enums.ParseMode.HTML)
                except:
                    pass
            await asyncio.sleep(delay)

            # Richest
            cursor = user_collection.find({}, {"_id":0,"id":1,"first_name":1,"balance":1})
            cdata = await cursor.to_list(length=None)
            cdata.sort(key=lambda x: x.get("balance",0), reverse=True)
            top_coins = cdata[:10]
            caption = build_coin_leaderboard_with_badges(top_coins)
            try:
                await message_obj.edit_caption(caption, parse_mode=enums.ParseMode.HTML, reply_markup=get_buttons("mtop"))
            except:
                try:
                    await message_obj.edit_text(caption, parse_mode=enums.ParseMode.HTML)
                except:
                    pass
            await asyncio.sleep(delay)
    except Exception:
        # swallow errors to avoid crashing background task
        return

# ---------- /rank command (send message then animate) ----------
@app.on_message(filters.command("rank"))
async def rank_cmd(client, message):
    # send initial users leaderboard (will be animated)
    cursor = user_collection.find({}, {"_id": 0, "id": 1, "first_name": 1, "characters": 1})
    data = await cursor.to_list(length=None)
    data.sort(key=lambda x: len(x.get("characters", [])), reverse=True)
    top_users = data[:10]
    caption = build_user_leaderboard_with_badges(top_users)

    sent = await message.reply_photo(
        photo=random.choice(PHOTO_URL),
        caption=caption,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=get_buttons("top")
    )

    # start animation task (non-blocking)
    asyncio.create_task(animate_leaderboard(sent, cycles=4, delay=2.0))

# ---------- /profile command ----------
@app.on_message(filters.command("profile"))
async def profile_cmd(client, message):
    # usage: /profile (self) or /profile <user_id or @username or reply>
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        parts = message.text.split()
        if len(parts) >= 2:
            try:
                # accept mention or id
                t = parts[1]
                if t.startswith("@"):
                    target = await client.get_users(t)
                else:
                    target = await client.get_users(int(t))
            except Exception:
                return await message.reply_text("Invalid user identifier.")

    if not target:
        target = message.from_user

    uid = target.id

    # fetch user doc
    user_doc = await user_collection.find_one({"id": uid})
    if not user_doc:
        return await message.reply_text("User not found in DB.")

    # compute rank by characters
    cursor = user_collection.find({}, {"_id":0,"id":1,"first_name":1,"characters":1})
    all_users = await cursor.to_list(length=None)
    all_users.sort(key=lambda x: len(x.get("characters", [])), reverse=True)
    total_users = len(all_users)
    rank = 0
    for idx, u in enumerate(all_users, start=1):
        if u.get("id") == uid:
            rank = idx
            break

    badge_emoji, badge_label = get_badge(rank, total_users)

    chars = len(user_doc.get("characters", []))
    balance = user_doc.get("balance", 0)

    caption = (
        f"<b>{html.escape(target.first_name)}</b> {badge_emoji}\n"
        f"{badge_label}\n\n"
        f"🧾 Characters Found: <b>{chars}</b>\n"
        f"💰 Balance: <b>{balance}</b>\n"
        f"🏅 Global Rank (by characters): <b>#{rank} / {total_users}</b>\n"
    )

    # try to send profile photo if present
    try:
        photos = await client.get_profile_photos(uid, limit=1)
        if photos.total_count > 0:
            await client.send_photo(chat_id=message.chat.id, photo=photos.photos[0].file_id, caption=caption, parse_mode=enums.ParseMode.HTML)
            return
    except Exception:
        pass

    # fallback: just send text
    await message.reply_text(caption, parse_mode=enums.ParseMode.HTML)
