import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "medication_reminder")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
users = db["users"]
