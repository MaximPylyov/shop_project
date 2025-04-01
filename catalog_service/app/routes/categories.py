import json
from typing import List
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from aioredis import Redis

from schemas import Product as ProductSchema, ProductCreate, ProductUpdate, Category as CategorySchema, CategoryCreate, CategoryUpdate 
from models import Product, Category  
from database import wait_for_db, get_session
from kafka_service import send_event
from redis_serivce import get_redis

from fastapi import APIRouter

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("/categories/", response_model=List[CategorySchema])
async def get_categories(redis: Redis = Depends(get_redis), db: AsyncSession = Depends(get_session)):
    categories = await redis.get("categories")
    if categories:
        return [CategorySchema(**item) for item in json.loads(categories)]
    else:
        try:
            result = await db.execute(select(Category))
            db_categories = result.scalars().all()
            await redis.set("categories", json.dumps([CategorySchema(**p.__dict__).dict() for p in db_categories]), ex=3600)
            return db_categories
        except SQLAlchemyError:
            raise HTTPException(status_code=500, detail="Ошибка при получении списка категорий")

@router.get("/categories/{category_id}", response_model=CategorySchema)
async def get_category_detail(category_id: int, db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(Category).where(Category.id == category_id))
        db_category = result.scalar_one_or_none()
        if db_category is None:
            raise HTTPException(status_code=404, detail="Указанная категория не найдена")
        
        return db_category
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при получении категории")

@router.post("/categories/", response_model=CategorySchema)
async def create_category(category: CategoryCreate, redis: Redis = Depends(get_redis), db: AsyncSession = Depends(get_session)):
    try:
        db_category = Category(**category.model_dump())
        db.add(db_category)
        await db.commit()
        await db.refresh(db_category)
        await redis.delete("categories")
        return db_category
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при создании категории")

@router.put("/categories/{category_id}", response_model=CategorySchema)
async def update_category(category_id: int, product: CategoryUpdate, redis: Redis = Depends(get_redis), db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(Category).where(Category.id == category_id))
        db_category = result.scalar_one_or_none()
        if db_category is None:
            raise HTTPException(status_code=404, detail="Указанная категория не найдена")
        setattr(db_category, "name", product.name)

        await db.commit()
        await db.refresh(db_category)
        await redis.delete("categories")
        return db_category
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при обновлении категории")

@router.delete("/categories/{category_id}")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(
            select(Category).filter(Category.id == category_id)
        )
        db_category = result.scalar_one_or_none()
        
        if db_category is None:
            raise HTTPException(status_code=404, detail="Указанная категория не найдена")
        
        await db.delete(db_category)
        await db.commit()
        return {"message": "Категория удалена"}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка базы данных при удалении категории")