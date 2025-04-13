import json
from typing import List
from fastapi import  Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from aioredis import Redis

from schemas import  Category as CategorySchema, CategoryCreate, CategoryUpdate 
from models import  Category  
from database import  get_session
from redis_serivce import get_redis
from auth_services import get_current_permissions, get_current_roles

from fastapi import APIRouter

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("/categories/", response_model=List[CategorySchema])
async def get_categories(permissions: set = Depends(get_current_permissions), redis: Redis = Depends(get_redis), db: AsyncSession = Depends(get_session)):
    if 'get_categories' not in permissions:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
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
async def get_category_detail(category_id: int, permissions: set = Depends(get_current_permissions), db: AsyncSession = Depends(get_session)):
    if 'get_categories' not in permissions:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
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
async def create_category(category: CategoryCreate, permissions: set = Depends(get_current_permissions), redis: Redis = Depends(get_redis), db: AsyncSession = Depends(get_session)):
    if 'create_category' not in permissions:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
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
async def update_category(category_id: int, product: CategoryUpdate, permissions: set = Depends(get_current_permissions), redis: Redis = Depends(get_redis), db: AsyncSession = Depends(get_session)):
    if 'update_category' not in permissions:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
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
async def delete_category(category_id: int, permissions: set = Depends(get_current_permissions), db: AsyncSession = Depends(get_session)):
    if 'delete_category' not in permissions:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
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