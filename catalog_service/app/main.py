import aioredis
import json
from typing import List
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select

from schemas import Product as ProductSchema, ProductCreate, ProductUpdate, Category as CategorySchema, CategoryCreate, CategoryUpdate 
from models import Product, Category  
from database import wait_for_db, get_session
from kafka_service import send_event

app = FastAPI(title="Catalog Service")

async def get_redis():
    redis = aioredis.from_url("redis://redis:6379", encoding="utf-8", decode_responses=True)
    try:
        yield redis
    finally:
        await redis.close()

@app.on_event("startup")
async def startup():
    app.state.db = await wait_for_db()

@app.get("/products/", response_model=List[ProductSchema], tags=["Products"])
async def get_products(db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(Product))
        db_products = result.scalars().all()
        return db_products
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Ошибка при получении товаров")

@app.get("/products/{product_id}", response_model=ProductSchema, tags=["Products"])
async def get_product_detail(product_id: int, db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        db_product = result.scalar_one_or_none()
        if db_product is None:
            raise HTTPException(status_code=404, detail="Указанный заказ не найден")
        return db_product
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Ошибка при получении товара")

@app.post("/products/", response_model=ProductSchema, tags=["Products"])
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(Category).where(Category.id == product.category_id))
        category = result.scalar_one_or_none()
        if category is None:
            raise HTTPException(status_code=404, detail="Категория не найдена")

        db_product = Product(**product.model_dump())
        db.add(db_product)
        await db.commit()
        await db.refresh(db_product)
        return db_product
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при создании товара")

@app.put("/products/{product_id}", response_model=ProductSchema, tags=["Products"])
async def update_product(product_id: int, product: ProductUpdate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(Product).where(Product.id == product_id))
        db_product = result.scalar_one_or_none()
        if db_product is None:
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
                raise HTTPException(status_code=404, detail="Категория не найдена")

        product_data = product.model_dump(exclude_unset=True)
        for field, value in product_data.items():
            setattr(db_product, field, value)

        await db.commit()
        await db.refresh(db_product)

        event = {
            "user_id": 1,
            "product_id": db_product.id,
            "old_data": old_data,
            "new_data": product_data,
            "action": "PRODUCT_UPDATED",
            "timestamp": datetime.utcnow().isoformat()
        }
        await send_event(event)
        return db_product
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при обновление товара")

@app.delete("/products/{product_id}", tags=["Products"])
async def delete_product(product_id: int, db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(
            select(Product).filter(Product.id == product_id)
        )
        db_product = result.scalar_one_or_none()
        
        if db_product is None:
            raise HTTPException(status_code=404, detail="Указанный продукт не найден")
        
        await db.delete(db_product)
        await db.commit()
        return {"message": "Товар удалён"}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка базы данных при удалении товара")

@app.get("/categories/", response_model=List[CategorySchema],  tags=["Categories"])
async def get_categories(redis: aioredis.Redis = Depends(get_redis), db: AsyncSession = Depends(get_session)):
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

@app.get("/categories/{category_id}", response_model=CategorySchema, tags=["Categories"])
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

@app.post("/categories/", response_model=CategorySchema, tags=["Categories"])
async def create_category(category: CategoryCreate, redis: aioredis.Redis = Depends(get_redis), db: AsyncSession = Depends(get_session)):
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

@app.put("/categories/{category_id}", response_model=CategorySchema, tags=["Categories"])
async def update_category(category_id: int, product: CategoryUpdate, redis: aioredis.Redis = Depends(get_redis), db: AsyncSession = Depends(get_session)):
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

@app.delete("/categories/{category_id}", tags=["Categories"])
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