from datetime import datetime
from os import getenv
from typing import List

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

from kafka_service import send_event

app = FastAPI(title="Reviews Service")


client = AsyncIOMotorClient(getenv("MONGODB_URL"))
db = client.reviews_db
reviews_collection = db.reviews


class ReviewCreate(BaseModel):
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


@app.post("/reviews/", response_model=ReviewCreate)
async def create_review(review: ReviewCreate):
    review_dict = review.dict()
    review_dict["_id"] = str(ObjectId())
    review_dict["created_at"] = datetime.utcnow()
    await reviews_collection.insert_one(review_dict)

    event = {
        "user_id": review.user_id,
        "product_id": review.product_id,
        "action": "REVIEW_CREATED",
        "timestamp": datetime.utcnow().isoformat()
    }
    await send_event(event)

    return review

@app.get("/reviews/{product_id}", response_model=List[ReviewShow])
async def get_reviews(product_id: int):
    reviews = await reviews_collection.find({"product_id": product_id}).to_list()
    if not reviews:
        raise HTTPException(status_code=404, detail="Не найдено отзывов для этого товара")
    return [ReviewShow(id=str(review["_id"]), **review) for review in reviews]

@app.delete("/reviews/{review_id}")
async def delete_review(review_id: str):
    result = await reviews_collection.delete_one({"_id": review_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Отзыв не найден")
    return {"message": "Отзыв удалён"}


