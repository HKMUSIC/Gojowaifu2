from TEAMZYRO import LOGGER, SUPPORT_CHAT_ID

async def send_start_message_async(client):
    START_CHAT_ID = int(os.getenv("START_CHAT_ID", "0"))

    # If not set → skip
    if START_CHAT_ID == 0:
        return

    try:
        # Try sending message
        await client.send_message(
            START_CHAT_ID,
            "🔵 Bot started successfully!"
        )

    except Exception as e:
        # Peer ID invalid OR user not available
        if "PEER_ID_INVALID" in str(e):
            print("[START] Cannot send start message → User not found or bot never met user.")
        else:
            print("[START] Unexpected error:", e)
