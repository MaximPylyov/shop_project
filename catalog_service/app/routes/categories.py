import json
from typing import List
from uuid import UUID
from fastapi import  Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from aioredis import Redis

from schemas import  Category as CategorySchema, CategoryCreate, CategoryUpdate 
from models import  Category  
from database import  get_session
from redis_serivce import get_redis
from auth_services import get_current_permissions, get_current_roles, get_current_user_id
from logger import logger

from fastapi import APIRouter

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("/categories/", response_model=List[CategorySchema])
async def get_categories(
    permissions: set = Depends(get_current_permissions),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id)
):
    if 'get_categories' not in permissions:
        logger.warning("Нет доступа к get_categories", extra={"user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    categories = await redis.get("categories")
    if categories:
        logger.info("Категории получены из кэша", extra={"user_id": str(user_id)})
        return [CategorySchema(**item) for item in json.loads(categories)]
    try:
        result = await db.execute(select(Category))
        db_categories = result.scalars().all()
        await redis.set(
            "categories",
            json.dumps([CategorySchema(**p.__dict__).dict() for p in db_categories]),
            ex=3600
        )
        logger.info(
            "Категории получены из БД и закешированы",
            extra={"count": len(db_categories), "user_id": str(user_id)}
        )
        return db_categories
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении списка категорий: {e}", extra={"user_id": str(user_id)})
        raise HTTPException(status_code=500, detail="Ошибка при получении списка категорий")

@router.get("/categories/{category_id}", response_model=CategorySchema)
async def get_category_detail(
    category_id: int,
    permissions: set = Depends(get_current_permissions),
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id)
):
    if 'get_categories' not in permissions:
        logger.info("Нет доступа к get_categories", extra={"category_id": category_id, "user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(select(Category).where(Category.id == category_id))
        db_category = result.scalar_one_or_none()
        if db_category is None:
            logger.warning(
                "Запрошена категория которой нет",
                extra={"category_id": category_id, "user_id": str(user_id)}
            )
            raise HTTPException(status_code=404, detail="Указанная категория не найдена")
        logger.info(
            "Успешно запрошена и возвращена категория",
            extra={"category_id": category_id, "category_name": db_category.name, "user_id": str(user_id)}
        )
        return db_category
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"Ошибка при получении категории: {e}",
            extra={"category_id": category_id, "user_id": str(user_id)}
        )
        raise HTTPException(status_code=500, detail="Ошибка при получении категории")

@router.post("/categories/", response_model=CategorySchema)
async def create_category(
    category: CategoryCreate,
    permissions: set = Depends(get_current_permissions),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id)
):
    if 'create_category' not in permissions:
        logger.warning("Нет доступа к create_category", extra={"category_name": category.name, "user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        db_category = Category(**category.model_dump())
        db.add(db_category)
        await db.commit()
        await db.refresh(db_category)
        await redis.delete("categories")
        logger.info(
            "Категория создана",
            extra={"category_id": db_category.id, "category_name": db_category.name, "user_id": str(user_id)}
        )
        return db_category
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            f"Ошибка при создании категории: {e}",
            extra={"category_name": category.name, "user_id": str(user_id)}
        )
        raise HTTPException(status_code=500, detail="Ошибка при создании категории")

@router.put("/categories/{category_id}", response_model=CategorySchema)
async def update_category(
    category_id: int,
    product: CategoryUpdate,
    permissions: set = Depends(get_current_permissions),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id)
):
    if 'update_category' not in permissions:
        logger.warning("Нет доступа к update_category", extra={"category_id": category_id, "user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(select(Category).where(Category.id == category_id))
        db_category = result.scalar_one_or_none()
        if db_category is None:
            logger.warning(
                "Попытка обновить несуществующую категорию",
                extra={"category_id": category_id, "user_id": str(user_id)}
            )
            raise HTTPException(status_code=404, detail="Указанная категория не найдена")
        old_name = db_category.name
        setattr(db_category, "name", product.name)
        await db.commit()
        await db.refresh(db_category)
        await redis.delete("categories")
        logger.info(
            "Категория обновлена",
            extra={
                "category_id": db_category.id,
                "old_name": old_name,
                "new_name": db_category.name,
                "user_id": str(user_id)
            }
        )
        return db_category
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            f"Ошибка при обновлении категории: {e}",
            extra={"category_id": category_id, "new_name": product.name, "user_id": str(user_id)}
        )
        raise HTTPException(status_code=500, detail="Ошибка при обновлении категории")

@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    permissions: set = Depends(get_current_permissions),
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id)
):
    if 'delete_category' not in permissions:
        logger.warning("Нет доступа к delete_category", extra={"category_id": category_id, "user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(select(Category).filter(Category.id == category_id))
        db_category = result.scalar_one_or_none()
        if db_category is None:
            logger.warning(
                "Попытка удалить несуществующую категорию",
                extra={"category_id": category_id, "user_id": str(user_id)}
            )
            raise HTTPException(status_code=404, detail="Указанная категория не найдена")
        await db.delete(db_category)
        await db.commit()
        logger.info(
            "Категория удалена",
            extra={"category_id": category_id, "category_name": db_category.name, "user_id": str(user_id)}
        )
        return {"message": "Категория удалена"}
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            f"Ошибка базы данных при удалении категории: {e}",
            extra={"category_id": category_id, "user_id": str(user_id)}
        )
        raise HTTPException(status_code=500, detail="Ошибка базы данных при удалении категории")