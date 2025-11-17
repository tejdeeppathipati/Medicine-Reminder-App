import os
import certifi
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "medication-reminder")

# Configure SSL for MongoDB Atlas connections
if "mongodb.net" in MONGO_URI or "mongodb+srv" in MONGO_URI:
    client = MongoClient(
        MONGO_URI,
        tlsCAFile=certifi.where()
    )
else:
    client = MongoClient(MONGO_URI)

db = client[MONGO_DB_NAME]
users = db["users"]