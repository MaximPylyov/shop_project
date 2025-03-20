from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
import os
import asyncio

DATABASE_URL = os.getenv("DATABASE_URL")

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_db():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

app = FastAPI(title="Orders Service")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    status = Column(String(16))
    total_price = Column(Numeric(32,2))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer)
    quantity = Column(Integer)
    price_at_moment = Column(Numeric(16,2))

    order_id = Column(Integer, ForeignKey("orders.id"))

async def wait_for_db():
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("Database connection successful!")
            return engine
        except Exception as e:
            print(f"Attempt {i+1}/{max_retries}: Database not ready... {str(e)}")
            if i < max_retries - 1:
                await asyncio.sleep(retry_interval)
    raise Exception("Could not connect to database")

@app.on_event("startup")
async def startup():
    app.state.db = await wait_for_db()

@app.get("/orders/", tags=["Orders"])
async def get_orders():
    return {"user_id": 1}

@app.get("/orders/{order_id}", tags=["Orders"])
async def get_order_detail(order_id: int):
    return {"user_id": 1}

@app.post("/orders/", tags=["Orders"])
async def create_order():
    return {"message": "Заказ создан"}

@app.put("/orders/{order_id}", tags=["Orders"])
async def update_order(order_id: int):
    return {"message": "Заказ обновлен"}

@app.delete("/orders/{order_id}", tags=["Orders"])
async def delete_order(order_id: int):
    return {"message": "Заказ удалён"}

app = FastAPI(title="Orders Service")



