from typing import List
from datetime import datetime
from fastapi import Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from uuid import UUID

from schemas import Product as ProductSchema, ProductCreate, ProductUpdate
from models import Product, Category  
from database import  get_session
from kafka_service import send_event
from auth_services import get_token_from_cookie, get_current_permissions, get_current_user_id
from logger import logger

from fastapi import APIRouter

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=List[ProductSchema])
async def get_products(
    permissions: set = Depends(get_current_permissions),
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id)
):
    if 'view_catalog' not in permissions:
        logger.warning("Нет доступа к view_catalog", extra={"user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(select(Product))
        db_products = result.scalars().all()
        logger.info("Получен список товаров", extra={"count": len(db_products), "user_id": str(user_id)})
        return db_products
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении товаров: {e}", extra={"user_id": str(user_id)})
        raise HTTPException(status_code=500, detail="Ошибка при получении товаров")

@router.get("/{product_id}", response_model=ProductSchema)
async def get_product_detail(
    product_id: int,
    permissions: set = Depends(get_current_permissions),
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id)
):
    if 'view_catalog' not in permissions:
        logger.warning("Нет доступа к view_catalog", extra={"product_id": product_id, "user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        db_product = result.scalar_one_or_none()
        if db_product is None:
            logger.warning("Запрошен несуществующий товар", extra={"product_id": product_id, "user_id": str(user_id)})
            raise HTTPException(status_code=404, detail="Указанный заказ не найден")
        logger.info("Получен товар", extra={"product_id": product_id, "product_name": db_product.name, "user_id": str(user_id)})
        return db_product
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при получении товара: {e}", extra={"product_id": product_id, "user_id": str(user_id)})
        raise HTTPException(status_code=500, detail="Ошибка при получении товара")

@router.post("/", response_model=ProductSchema)
async def create_product(
    product: ProductCreate, 
    permissions: set = Depends(get_current_permissions),
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id)
):
    try:
        if 'create_product' not in permissions:
            logger.warning("Нет доступа к create_product", extra={"user_id": str(user_id)})
            raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
        result = await db.execute(select(Category).where(Category.id == product.category_id))
        category = result.scalar_one_or_none()
        if category is None:
            logger.warning("Категория не найдена при создании товара", extra={"category_id": product.category_id, "user_id": str(user_id)})
            raise HTTPException(status_code=404, detail="Категория не найдена")

        db_product = Product(**product.model_dump())
        db.add(db_product)
        await db.commit()
        await db.refresh(db_product)
        logger.info("Товар создан", extra={"product_id": db_product.id, "product_name": db_product.name, "user_id": str(user_id)})
        return db_product
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Ошибка при создании товара: {e}", extra={"user_id": str(user_id)})
        raise HTTPException(status_code=500, detail="Ошибка при создании товара")

@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    permissions: set = Depends(get_current_permissions),
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id)
):
    if 'update_product' not in permissions:
        logger.warning("Нет доступа к update_product", extra={"product_id": product_id, "user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        db_product = result.scalar_one_or_none()
        if db_product is None:
            logger.warning("Попытка обновить несуществующий товар", extra={"product_id": product_id, "user_id": str(user_id)})
            raise HTTPException(status_code=404, detail="Указанный товар не найден")
        
        old_data = {
            "name": db_product.name,
            "price": db_product.price,
            "category_id": db_product.category_id,
        }

        if product.category_id is not None:
            result = await db.execute(select(Category).where(Category.id == product.category_id))
            category = result.scalar_one_or_none()
            if category is None:
                logger.warning("Категория не найдена при обновлении товара", extra={"category_id": product.category_id, "user_id": str(user_id)})
                raise HTTPException(status_code=404, detail="Категория не найдена")

        product_data = product.model_dump(exclude_unset=True)
        for field, value in product_data.items():
            setattr(db_product, field, value)

        await db.commit()
        await db.refresh(db_product)

        logger.info(
            "Товар обновлён",
            extra={
                "product_id": db_product.id,
                "old_data": old_data,
                "new_data": product_data,
                "user_id": str(user_id)
            }
        )

        event = {
            "user_id": str(user_id),
            "product_id": db_product.id,
            "old_data": old_data,
            "new_data": product_data,
            "action": "PRODUCT_UPDATED",
            "timestamp": datetime.utcnow().isoformat()
        }
        await send_event(event)
        return db_product
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Ошибка при обновлении товара: {e}", extra={"product_id": product_id, "user_id": str(user_id)})
        raise HTTPException(status_code=500, detail="Ошибка при обновление товара")

@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    permissions: set = Depends(get_current_permissions),
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id)
):
    try:
        if 'delete_product' not in permissions:
            logger.warning("Нет доступа к delete_product", extra={"product_id": product_id, "user_id": str(user_id)})
            raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
        result = await db.execute(
            select(Product).filter(Product.id == product_id)
        )
        db_product = result.scalar_one_or_none()
        
        if db_product is None:
            logger.warning("Попытка удалить несуществующий товар", extra={"product_id": product_id, "user_id": str(user_id)})
            raise HTTPException(status_code=404, detail="Указанный продукт не найден")
        
        await db.delete(db_product)
        await db.commit()
        logger.info("Товар удалён", extra={"product_id": product_id, "product_name": db_product.name, "user_id": str(user_id)})
        return {"message": "Товар удалён"}
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Ошибка базы данных при удалении товара: {e}", extra={"product_id": product_id, "user_id": str(user_id)})
        raise HTTPException(status_code=500, detail="Ошибка базы данных при удалении товара")