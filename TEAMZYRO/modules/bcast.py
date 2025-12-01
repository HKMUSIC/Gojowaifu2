import asyncio
from pyrogram import filters
from pyrogram.errors import PeerIdInvalid, FloodWait
from TEAMZYRO import user_collection, group_collection, app, require_power

@app.on_message(filters.command("bcast"))
@require_power("bcast")
async def broadcast(_, message):
    replied = message.reply_to_message
    if not replied:
        return await message.reply_text("❌ Please reply to a message to broadcast it.")

    progress = await message.reply_text("📢 Starting broadcast...")

    user_sent = 0
    group_sent = 0
    failed = 0
    count = 0

    # -------------------------
    #  FORWARD FUNCTION
    # -------------------------
    async def forward_msg(chat_id):
        nonlocal user_sent, group_sent, failed, count

        try:
            await replied.forward(chat_id)  # ⭐ PURE FORWARD
            count += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await forward_msg(chat_id)
        except:
            failed += 1
            return

        # Rate limit
        if count % 7 == 0:
            await asyncio.sleep(2)

    # -------------------------
    #  UPDATE PROGRESS
    # -------------------------
    async def update_progress():
        try:
            await progress.edit_text(
                f"📢 Broadcast running...\n"
                f"👤 Users done: {user_sent}\n"
                f"👥 Groups done: {group_sent}\n"
                f"❌ Failed: {failed}"
            )
        except:
            pass

    # -------------------------
    #  SEND TO USERS
    # -------------------------
    async for user in user_collection.find({}):
        uid = user.get("id")
        if not uid:
            continue

        await forward_msg(uid)
        user_sent += 1

        if user_sent % 100 == 0:
            await update_progress()

    # -------------------------
    #  SEND TO GROUPS
    # -------------------------
    unique_groups = set()

    async for group in group_collection.find({}):
        gid = group.get("group_id")
        if not gid:
            continue

        if gid not in unique_groups:
            unique_groups.add(gid)
            await forward_msg(gid)
            group_sent += 1

            if group_sent % 50 == 0:
                await update_progress()

    # -------------------------
    #  FINAL REPORT
    # -------------------------
    await progress.edit_text(
        f"✅ Broadcast completed!\n"
        f"👤 Users: {user_sent}\n"
        f"👥 Groups: {group_sent}\n"
        f"❌ Failed: {failed}"
    )
