from fastapi import Depends, HTTPException, Request
from uuid import UUID
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
from auth_services import get_current_permissions, get_current_user_id
from logger import logger

import httpx
import aioredis


from fastapi import APIRouter

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/")
async def create_order(
    request: Request,
    items: List[Item], 
    user_id: UUID = Depends(get_current_user_id), 
    permissions: set = Depends(get_current_permissions), 
    redis: aioredis.Redis = Depends(get_redis), 
    db: AsyncSession = Depends(get_session)
):
    if 'create_order' not in permissions:
        logger.warning("Ошибка доступа к create_order", extra={"user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")

    token = request.cookies.get("access_token")
    if not token:
        logger.warning("Попытка доступа без access_token в cookie", extra={"path": request.url.path, "client": request.client.host})
        raise HTTPException(status_code=401, detail="Отсутствует токен авторизации")
    
    try:
        prices = {}
        total_prices = {}
        headers = {"Cookie": f"access_token={token}"}
        async with httpx.AsyncClient() as client:  
            for item in items:
                product_id = item.product_id
                quantity = item.quantity
                try:
                    response = await client.get(
                        f"http://host.docker.internal:8001/products/{product_id}",
                        headers=headers
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logger.error(f"Ошибка при получении товара {e}", extra={"user_id": str(user_id)})
                    raise HTTPException(status_code=e.response.status_code, detail=f"Ошибка при получении товара {e}")
                except httpx.ConnectError:
                    logger.error("Сервер продуктов недоступен", extra={"user_id": str(user_id)})
                    raise HTTPException(status_code=503, detail="Сервер продуктов недоступен")
                product = response.json()
                prices[product_id] = product["price"]
                total_prices[product_id] = product["price"] * quantity

        eur_rate = await redis.get('exchange_rates')
        
        if not eur_rate:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://host.docker.internal:8004/exchange-rates/latest")
                eur_rate = response.json()["rate"]
                logger.info("Забрали курс из БД", extra={"user_id": str(user_id), "rate": eur_rate})
        else:
            logger.info("Забрали курс из кэша", extra={"user_id": str(user_id), "rate": eur_rate})

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
        logger.info("Добавили запись заказа в БД", extra={"user_id": str(user_id), "order_id": new_order.id, "total_price": total_price})

        event = {
            "user_id": str(user_id),
            "order_id": new_order.id,  
            "total_price": total_price,
            "action": "ORDER_CREATED",
            "timestamp": datetime.utcnow().isoformat(),
            "token": token
        }
        await send_event(event)
        
        for item in items:
            order_item = OrderItem(order_id=new_order.id, product_id=item.product_id, quantity=item.quantity, price_at_moment=prices[item.product_id])
            db.add(order_item)
        logger.info("Добавили товары заказа в order_item", extra={"user_id": str(user_id)})

        await db.commit()
        
        return {"message": "Заказ создан", "order_id": new_order.id}
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Ошибка при создании заказа: {e}", extra={"user_id": str(user_id)})
        raise HTTPException(status_code=500, detail=f"Ошибка при создании заказа: {e}")

@router.delete("/{order_id}")
async def delete_order(
    order_id: int,
    permissions: set = Depends(get_current_permissions),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session)
):
    if 'delete_order' not in permissions:
        logger.warning("Ошибка доступа к delete_order", extra={"order_id": order_id, "user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(
            select(Order).filter(Order.id == order_id)
        )
        db_order = result.scalar_one_or_none()

        if db_order is None:
            logger.warning("Попытка удалить несуществующий заказ", extra={"order_id": order_id, "user_id": str(user_id)})
            raise HTTPException(status_code=404, detail="Указанный заказ не найден")
        
        await db.delete(db_order)
        await db.execute(
            delete(OrderItem).where(OrderItem.order_id == order_id)
        )
        await db.commit()
        logger.info("Заказ и связанные товары удалены", extra={"order_id": order_id, "user_id": str(user_id)})
        return {"message": "Заказ удалён"}

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Ошибка базы данных при удалении заказа: {e}", extra={"order_id": order_id, "user_id": str(user_id)})
        raise HTTPException(status_code=500, detail="Ошибка базы данных при удалении заказа")

@router.patch("/{order_id}")
async def update_order_status(
    order_id: int,
    status: str,
    permissions: set = Depends(get_current_permissions),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session)
):
    if 'update_order_status' not in permissions:
        logger.warning("Ошибка доступа к update_order_status", extra={"order_id": order_id, "user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(select(Order).where(Order.id == order_id))
        db_order = result.scalar_one_or_none()
        
        if db_order is None:
            logger.warning("Попытка обновить статус несуществующего заказа", extra={"order_id": order_id, "status": status, "user_id": str(user_id)})
            raise HTTPException(status_code=404, detail="Указанный заказ не найден")
        
        db_order.status = status
        db_order.updated_at = datetime.utcnow()  # Обновляем время обновления
        
        await db.commit()
        logger.info("Статус заказа обновлён", extra={"order_id": db_order.id, "status": status, "user_id": str(user_id)})
        return {"message": "Статус заказа обновлён", "order_id": db_order.id}
    
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Ошибка базы данных при обновлении заказа: {e}", extra={"order_id": order_id, "status": status, "user_id": str(user_id)})
        raise HTTPException(status_code=500, detail="Ошибка базы данных при обновлении заказа")

@router.get("/{order_id}", response_model=OrderSchema)
async def get_order(
    order_id: int,
    permissions: set = Depends(get_current_permissions),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session)
):
    if 'view_orders' not in permissions:
        logger.warning("Ошибка доступа к get_order", extra={"order_id": order_id, "user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(select(Order).where(Order.id == order_id))
        db_order = result.scalar_one_or_none()
        if db_order is None:
            logger.warning("Попытка получить несуществующий заказ", extra={"order_id": order_id, "user_id": str(user_id)})
            raise HTTPException(status_code=404, detail="Указанный заказ не найден")
        
        logger.info("Получен заказ", extra={"order_id": order_id, "user_id": str(user_id)})
        return db_order

    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Ошибка базы данных при получении заказа: {e}", extra={"order_id": order_id, "user_id": str(user_id)})
        raise HTTPException(status_code=500, detail="Ошибка базы данных при получении заказа")

@router.put("/{order_id}")
async def modif_order(
    order_id: int,
    order: OrderUpdate,
    permissions: set = Depends(get_current_permissions),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session)
):
    if 'update_order' not in permissions:
        logger.warning("Ошибка доступа к modif_order", extra={"order_id": order_id, "user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(select(Order).where(Order.id == order_id))
        db_order = result.scalar_one_or_none()
        
        if db_order is None:
            logger.warning("Попытка изменить несуществующий заказ", extra={"order_id": order_id, "user_id": str(user_id)})
            raise HTTPException(status_code=404, detail="Указанный заказ не найден")
        
        update_data = order.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_order, field, value)

        db_order.updated_at=datetime.utcnow()   
        await db.commit()
        logger.info("Заказ обновлен", extra={"order_id": db_order.id, "update_data": update_data, "user_id": str(user_id)})
        return {"message": "Заказ обновлен", "order_id": db_order.id}
    
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Ошибка базы данных при изменении заказа: {e}", extra={"order_id": order_id, "user_id": str(user_id)})
        raise HTTPException(status_code=500, detail="Ошибка базы данных при изменении заказа")

@router.get("/", response_model=List[OrderSchema])
async def get_all_orders(
    permissions: set = Depends(get_current_permissions),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_session)
):
    if 'view_orders' not in permissions:
        logger.warning("Ошибка доступа к get_all_orders", extra={"user_id": str(user_id)})
        raise HTTPException(status_code=403, detail="У вас нет доступа к этому действию")
    try:
        result = await db.execute(select(Order))
        orders = result.scalars().all()
        logger.info("Получен список всех заказов", extra={"orders_count": len(orders), "user_id": str(user_id)})
        return orders
    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при получении заказов: {e}", extra={"user_id": str(user_id)})
        raise HTTPException(status_code=500, detail="Ошибка базы данных при получении заказов")