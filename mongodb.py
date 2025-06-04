import pymongo
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "CODE_GENERATOR"

try:
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    print("MongoDB connection: SUCCESS")
except Exception as e:
    print(f"MongoDB connection: FAILED ({e})")

db = client[DB_NAME]
users_collection = db["users"]