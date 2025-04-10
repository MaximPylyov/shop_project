from fastapi import Depends, HTTPException
from database import  get_session  # Импортируем необходимые функции и классы
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from typing import List
from models import Order, OrderItem
from schemas import OrderSchema, OrderUpdate, Item
from datetime import datetime  # Импортируем datetime
from sqlalchemy import delete
from kafka_service import send_event
from redis_service import get_redis

import httpx
import aioredis


from fastapi import APIRouter

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/")
async def create_order(user_id: int, items: List[Item], redis: aioredis.Redis = Depends(get_redis), db: AsyncSession = Depends(get_session)):
    try:
        prices = {}
        total_prices = {}
        async with httpx.AsyncClient() as client:  # Создаем асинхронный клиент
            for item in items:
                product_id = item.product_id
                quantity = item.quantity
                try:
                    response = await client.get(f"http://host.docker.internal:8001/products/{product_id}")
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    raise HTTPException(status_code=e.response.status_code, detail=f"Ошибка при получении товара")
                except httpx.ConnectError:
                    raise HTTPException(status_code=503, detail="Сервер продуктов недоступен")
                product = response.json()
                prices[product_id] = product["price"]
                total_prices[product_id] = product["price"] * quantity

        eur_rate = await redis.get('exchange_rates')
        if not eur_rate:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://host.docker.internal:8004/exchange-rates/latest")
                eur_rate = response.json()["rate"]


        total_price = sum(total_prices.values()) * float(eur_rate)
        new_order = Order(
            user_id=user_id,
            status="CREATED",
            total_price=total_price,
            created_at=datetime.utcnow(),  
            updated_at=datetime.utcnow()   
        )
        db.add(new_order)
        await db.flush()  
        
        event = {
            "user_id": user_id,
            "order_id": new_order.id,  
            "total_price": total_price,
            "action": "ORDER_CREATED",
            "timestamp": datetime.utcnow().isoformat()
        }
        await send_event(event)
        
        for item in items:
            order_item = OrderItem(order_id=new_order.id, product_id=item.product_id, quantity=item.quantity, price_at_moment=prices[item.product_id])
            db.add(order_item)
        
        await db.commit()
        
        return {"message": "Заказ создан", "order_id": new_order.id}
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при создании заказа: {e}")

@router.delete("/{order_id}")
async def delete_order(order_id: int, db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(
            select(Order).filter(Order.id == order_id)
        )
        db_order = result.scalar_one_or_none()

        if db_order is None:
            raise HTTPException(status_code=404, detail="Указанный заказ не найден")
        
        await db.delete(db_order)
        await db.execute(
            delete(OrderItem).where(OrderItem.order_id == order_id)
        )
        await db.commit()
        return {"message": "Заказ удалён"}

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка базы данных при удалении заказа")

@router.patch("/{order_id}")
async def update_order_status(order_id: int, status: str, db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(Order).where(Order.id == order_id))
        db_order = result.scalar_one_or_none()
        
        if db_order is None:
            raise HTTPException(status_code=404, detail="Указанный заказ не найден")
        
        db_order.status = status

        db_order.updated_at = datetime.utcnow()  # Обновляем время обновления
        
        await db.commit()
        return {"message": "Статус заказа обновлён", "order_id": db_order.id}
    
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка базы данных при обновлении заказа")

@router.get("/{order_id}", response_model=OrderSchema)
async def get_order(order_id: int, db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(Order).where(Order.id == order_id))
        db_order = result.scalar_one_or_none()
        if db_order is None:
            raise HTTPException(status_code=404, detail="Указанный заказ не найден")
        
        return db_order

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка базы данных при получении заказа")


@router.put("/{order_id}")
async def modif_order(order_id: int, order: OrderUpdate, db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(select(Order).where(Order.id == order_id))
        db_order = result.scalar_one_or_none()
        
        if db_order is None:
            raise HTTPException(status_code=404, detail="Указанный заказ не найден")
        
        update_data = order.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_order, field, value)

        db_order.updated_at=datetime.utcnow()   
        await db.commit()  
        return {"message": "Заказ обновлен", "order_id": db_order.id}
    
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка базы данных при изменении заказа")