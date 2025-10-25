# Database.py
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection URI (heroku me set karo as env variable)
import os
MONGO_URI = os.getenv("MONGO_URI")  # set in Heroku config vars

client = AsyncIOMotorClient(MONGO_URI)
db = client["TEAMZYRO"]  # database name

# Collections
user_collection = db["users"]         # users data
characters_col = db["characters"]     # waifu/characters data
