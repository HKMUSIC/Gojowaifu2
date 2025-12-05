from TEAMZYRO import LOGGER, SUPPORT_CHAT_ID

async def send_start_message_async(client):
    try:
        await client.send_photo(
            SUPPORT_CHAT_ID,
            photo="https://telegra.ph/file/4bfc31a4.jpg",
            caption="Bot Started Successfully!"
        )
    except Exception as e:
        LOGGER("START").error(f"Failed to send start message: {e}")
