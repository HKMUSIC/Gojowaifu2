from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import app
import random

HUG_PHOTO = "https://files.catbox.moe/s5d954.jpg"   # ❤️ Your Image

# ------------------ /hug command ------------------

@app.on_message(filters.command("hug"))
async def hug_request(_, message):
    asker = message.from_user

    # Target user selection
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        return await message.reply_text(
            "❌ Please reply to someone to send a hug request!"
        )

    if target.id == asker.id:
        return await message.reply_text("😂 You can't hug yourself!")

    # Inline Buttons
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🤝 Accept", callback_data=f"hug_accept_{asker.id}"),
                InlineKeyboardButton("❌ Decline", callback_data=f"hug_decline_{asker.id}")
            ]
        ]
    )

    await message.reply_text(
        f"💞 **{asker.mention} wants to hug {target.mention}!**\n"
        f"Do you accept the hug request?",
        reply_markup=keyboard
    )

# ------------------ ACCEPT BUTTON ------------------

@app.on_callback_query(filters.regex("^hug_accept_"))
async def hug_accept(_, query):
    asker_id = int(query.data.split("_")[2])
    accepter = query.from_user

    # Check if accepter == target
    if accepter.id != query.message.reply_to_message.from_user.id:
        return await query.answer("❌ This hug request is not for you!", show_alert=True)

    asker = query.message.reply_to_message.from_user

    await query.message.edit_text(
        f"💞 **{accepter.mention} accepted {asker.mention}'s hug request!**"
    )

    # sending hug image
    await query.message.reply_photo(
        photo=HUG_PHOTO,
        caption=f"🤗 **{asker.mention} hugged {accepter.mention}** 💞"
    )

    await query.answer("❤️ Hug accepted!")

# ------------------ DECLINE BUTTON ------------------

@app.on_callback_query(filters.regex("^hug_decline_"))
async def hug_decline(_, query):
    asker_id = int(query.data.split("_")[2])
    decliner = query.from_user

    if decliner.id != query.message.reply_to_message.from_user.id:
        return await query.answer("❌ This decline button is not for you!", show_alert=True)

    asker = query.message.reply_to_message.from_user

    await query.message.edit_text(
        f"💔 **{decliner.mention} declined {asker.mention}'s hug request...**"
    )

    await query.answer("😢 Declined.")
