from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from TEAMZYRO import app
import random

HUG_PHOTO = "https://files.catbox.moe/s5d954.jpg"

# ------------------ /hug command ------------------

@app.on_message(filters.command("hug"))
async def hug_request(_, message):

    if not message.reply_to_message:
        return await message.reply_text("❌ Please reply to someone to send a hug request!")

    asker = message.from_user
    target = message.reply_to_message.from_user

    if asker.id == target.id:
        return await message.reply_text("😂 You cannot hug yourself!")

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🤝 Accept",
                    callback_data=f"hug_accept:{asker.id}:{target.id}"
                ),
                InlineKeyboardButton(
                    "❌ Decline",
                    callback_data=f"hug_decline:{asker.id}:{target.id}"
                )
            ]
        ]
    )

    await message.reply_text(
        f"💞 **{asker.mention} wants to hug {target.mention}!**\nDo you accept the hug?",
        reply_markup=keyboard
    )


# ------------------ ACCEPT BUTTON ------------------

@app.on_callback_query(filters.regex("^hug_accept"))
async def hug_accept(_, query):

    _, asker_id, target_id = query.data.split(":")
    asker_id = int(asker_id)
    target_id = int(target_id)

    # Only the target user can accept
    if query.from_user.id != target_id:
        return await query.answer("❌ This hug request is not for you!", show_alert=True)

    # Edit original message
    await query.message.edit_text(
        f"💞 **{query.from_user.mention} accepted <a href='tg://user?id={asker_id}'>this</a> hug request!**",
        disable_web_page_preview=True
    )

    # Send hug photo
    await query.message.reply_photo(
        HUG_PHOTO,
        caption=f"🤗 **<a href='tg://user?id={asker_id}'>Someone</a> hugged {query.from_user.mention}** 💞"
    )

    await query.answer("❤️ Hug accepted!")


# ------------------ DECLINE BUTTON ------------------

@app.on_callback_query(filters.regex("^hug_decline"))
async def hug_decline(_, query):

    _, asker_id, target_id = query.data.split(":")
    asker_id = int(asker_id)
    target_id = int(target_id)

    # Only the target user can decline
    if query.from_user.id != target_id:
        return await query.answer("❌ Not for you!", show_alert=True)

    await query.message.edit_text(
        f"💔 **{query.from_user.mention} declined <a href='tg://user?id={asker_id}'>this</a> hug request...**",
        disable_web_page_preview=True
    )

    await query.answer("😢 Declined.")
