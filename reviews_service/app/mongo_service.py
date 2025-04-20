from motor.motor_asyncio import AsyncIOMotorClient
from bson.binary import UuidRepresentation
from os import getenv

client = AsyncIOMotorClient(
    getenv("MONGODB_URL"),
    uuidRepresentation='standard'
)
db = client.reviews_db
reviews_collection = db.reviews
