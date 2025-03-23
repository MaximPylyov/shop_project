from os import getenv
from fastapi import FastAPI, HTTPException
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field

app = FastAPI(title="Reviews Service")


client = AsyncIOMotorClient(getenv("MONGODB_URL", "mongodb://mongo:27017"))
db = client.reviews_db
reviews_collection = db.reviews


class Review(BaseModel):
    product_id: int
    user_id: int
    rating: int = Field(..., ge=1, le=5)  
    comment: str

class ReviewShow(BaseModel):
    id: str = Field(..., pattern="^[0-9a-f]{24}$")
    product_id: int
    user_id: int 
    rating: int = Field(..., ge=1, le=5)  
    comment: str 
    created_at: datetime


@app.post("/reviews/", response_model=Review)
async def create_review(review: Review):
    review_dict = review.dict()
    review_dict["_id"] = str(ObjectId())
    review_dict["created_at"] = datetime.utcnow()
    await reviews_collection.insert_one(review_dict)
    return review

@app.get("/reviews/{product_id}", response_model=List[ReviewShow])
async def get_reviews(product_id: int):
    reviews = await reviews_collection.find({"product_id": product_id}).to_list()
    return [ReviewShow(id=str(review["_id"]), **review) for review in reviews]

@app.delete("/reviews/{review_id}")
async def delete_review(review_id: str):
    result = await reviews_collection.delete_one({"_id": review_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"detail": "Review deleted"}


