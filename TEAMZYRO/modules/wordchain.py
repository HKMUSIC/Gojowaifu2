import json
import random
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters

WORDLIST = []
ACTIVE_GAMES = {}

# Load English words
def load_words():
    global WORDLIST
    with open("downloads/words.txt", "r") as f:
        WORDLIST = [w.strip().lower() for w in f.readlines() if len(w.strip()) > 2]

load_words()


# ----------------------------
# START GAME
# ----------------------------
def wordchain_start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if chat_id in ACTIVE_GAMES:
        return update.message.reply_text("⚠️ A wordchain game is already running here!")

    ACTIVE_GAMES[chat_id] = {
        "players": [],
        "current_word": None,
        "turn": 0,
        "running": True
    }

    update.message.reply_text(
        "🎮 *WordChain Game Started!*\nSend /join to join the game.",
        parse_mode="Markdown"
    )


# ----------------------------
# JOIN GAME
# ----------------------------
def join_game(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id not in ACTIVE_GAMES:
        return update.message.reply_text("❌ No game running. Start using /wordchainstart")

    if user.id in ACTIVE_GAMES[chat_id]["players"]:
        return update.message.reply_text("You already joined!")

    ACTIVE_GAMES[chat_id]["players"].append(user.id)
    update.message.reply_text(f"🔥 {user.first_name} joined the game!")


# ----------------------------
# STOP GAME
# ----------------------------
def wordchain_stop(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if chat_id not in ACTIVE_GAMES:
        return update.message.reply_text("❌ No active WordChain game.")

    del ACTIVE_GAMES[chat_id]
    update.message.reply_text("🛑 WordChain game stopped!")


# ----------------------------
# HANDLE WORD ANSWERS
# ----------------------------
def handle_words(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    msg = update.message.text.lower()

    if chat_id not in ACTIVE_GAMES:
        return

    game = ACTIVE_GAMES[chat_id]

    if not game["players"]:
        return update.message.reply_text("⚠️ No players joined yet!")

    current_player = game["players"][game["turn"]]

    # Check turn
    if update.effective_user.id != current_player:
        return

    # First word
    if not game["current_word"]:
        if msg in WORDLIST:
            game["current_word"] = msg
            game["turn"] = (game["turn"] + 1) % len(game["players"])
            return update.message.reply_text(f"✔ Word accepted: *{msg}*", parse_mode="Markdown")
        else:
            return update.message.reply_text("❌ Invalid word!")

    # Check starts with last letter
    if msg[0] != game["current_word"][-1]:
        return update.message.reply_text(
            f"❌ Your word must begin with *{game['current_word'][-1]}*",
            parse_mode="Markdown"
        )

    if msg not in WORDLIST:
        return update.message.reply_text("❌ Invalid English word!")

    # Success
    game["current_word"] = msg
    game["turn"] = (game["turn"] + 1) % len(game["players"])
    update.message.reply_text(f"✔ Correct! Next word must start with *{msg[-1]}*.", parse_mode="Markdown")


# ----------------------------
# ADD HANDLERS
# ----------------------------
def add_wordchain_handlers(dp):
    dp.add_handler(CommandHandler("wordchainstart", wordchain_start))
    dp.add_handler(CommandHandler("wordchainstop", wordchain_stop))
    dp.add_handler(CommandHandler("join", join_game))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_words))
