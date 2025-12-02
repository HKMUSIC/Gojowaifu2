from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import app

# ---------- CUSTOM IMAGES ----------
KISS_PHOTO = "https://files.catbox.moe/p949ei.jpg"
PROPOSE_PHOTO = "https://files.catbox.moe/oez12u.jpg"
KILL_PHOTO = "https://files.catbox.moe/1o1erc.jpg"


# --------------- GENERIC FUNCTION ----------------

async def send_action(message, action_name, photo_url):
    sender = message.from_user

    if not message.reply_to_message:
        return await message.reply_text("❌ Please reply to someone to use this command!")

    target = message.reply_to_message.from_user

    if sender.id == target.id:
        return await message.reply_text("😂 You can't perform this action on yourself!")

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"act_yes_{action_name}_{sender.id}"),
                InlineKeyboardButton("❌ Decline", callback_data=f"act_no_{action_name}_{sender.id}")
            ]
        ]
    )

    await message.reply_text(
        f"**{sender.mention} wants to {action_name} {target.mention}!** 💞\n"
        f"Do you accept?",
        reply_markup=keyboard
    )


# -------------------- /kiss -----------------------

@app.on_message(filters.command("kiss"))
async def kiss(_, message):
    await send_action(message, "kiss", KISS_PHOTO)


# -------------------- /propose -----------------------

@app.on_message(filters.command(["propose", "Propose"]))
async def propose(_, message):
    await send_action(message, "propose", PROPOSE_PHOTO)


# -------------------- /kill -----------------------

@app.on_message(filters.command("kill"))
async def kill(_, message):
    await send_action(message, "kill", KILL_PHOTO)


# ------------------- CALLBACK HANDLER ---------------------

@app.on_callback_query(filters.regex("^act_yes_"))
async def action_accept(_, query):
    _, _, action, sender_id = query.data.split("_")
    sender_id = int(sender_id)

    sender = query.message.reply_to_message.from_user
    acceptor = query.from_user

    if acceptor.id != sender.id:
        return await query.answer("❌ This request is not for you!", show_alert=True)

    # Select photo based on action
    photo_map = {
        "kiss": KISS_PHOTO,
        "propose": PROPOSE_PHOTO,
        "kill": KILL_PHOTO
    }

    await query.message.edit_text(
        f"💞 **{acceptor.mention} accepted {sender.mention}'s {action} request!**"
    )

    await query.message.reply_photo(
        photo=photo_map[action],
        caption=f"❤️ **{sender.mention} {action}ed {acceptor.mention}!** 💞"
    )

    await query.answer("Accepted!")


@app.on_callback_query(filters.regex("^act_no_"))
async def action_decline(_, query):
    _, _, action, sender_id = query.data.split("_")
    sender_id = int(sender_id)

    sender = query.message.reply_to_message.from_user
    decliner = query.from_user

    if decliner.id != sender.id:
        return await query.answer("❌ This request is not for you!", show_alert=True)

    await query.message.edit_text(
        f"💔 **{decliner.mention} declined {sender.mention}'s {action} request...**"
    )

    await query.answer("Declined.")
