
from datetime import datetime
from os import getenv
from typing import List

from bson import ObjectId
from fastapi import FastAPI, HTTPException, APIRouter, Depends
from uuid import UUID

from auth_services import get_current_permissions, get_current_user_id
from kafka_service import send_event
from mongo_service import reviews_collection
from schemas import ReviewCreate, ReviewShow


router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("/", response_model=ReviewCreate)
async def create_review(review: ReviewCreate, user_id: UUID = Depends(get_current_user_id), permissions: set = Depends(get_current_permissions)):
    if 'create_review' not in permissions:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    
    review_dict = review.dict()
    review_dict["user_id"] = user_id
    review_dict["_id"] = str(ObjectId())
    review_dict["created_at"] = datetime.utcnow()
    await reviews_collection.insert_one(review_dict)

    event = {
        "user_id": str(user_id),
        "product_id": review.product_id,
        "action": "REVIEW_CREATED",
        "timestamp": datetime.utcnow().isoformat()
    }
    await send_event(event)

    return review

@router.get("/{product_id}", response_model=List[ReviewShow])
async def get_reviews(product_id: int, permissions: set = Depends(get_current_permissions)):
    if 'get_reviews' not in permissions:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    reviews = await reviews_collection.find({"product_id": product_id}).to_list()
    if not reviews:
        raise HTTPException(status_code=404, detail="Не найдено отзывов для этого товара")
    return [ReviewShow(id=str(review["_id"]), **review) for review in reviews]

@router.delete("/{review_id}")
async def delete_review(review_id: str, permissions: set = Depends(get_current_permissions)):
    if 'delete_review' not in permissions:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    result = await reviews_collection.delete_one({"_id": review_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Отзыв не найден")
    return {"message": "Отзыв удалён"}