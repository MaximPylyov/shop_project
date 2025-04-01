from motor.motor_asyncio import AsyncIOMotorClient

from os import getenv

client = AsyncIOMotorClient(getenv("MONGODB_URL"))
db = client.reviews_db
reviews_collection = db.reviews
