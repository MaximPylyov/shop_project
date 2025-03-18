from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from tenacity import retry, stop_after_attempt, wait_exponential
import time
import os


DATABASE_URL = os.getenv("DATABASE_URL")

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_db():
    engine = create_engine(DATABASE_URL)
    try:
        engine.connect()
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
        raise
    return engine

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



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


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Orders Service")

def wait_for_db():
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            engine = create_engine(DATABASE_URL)
            engine.connect()
            print("Database connection successful!")
            return engine
        except Exception as e:
            print(f"Attempt {i+1}/{max_retries}: Database not ready... {str(e)}")
            if i < max_retries - 1:
                time.sleep(retry_interval)
    raise Exception("Could not connect to database")

@app.on_event("startup")
async def startup():
    app.state.db = wait_for_db()


@app.get("/orders/", tags=["Orders"])
async def get_orders():
    return {"user_id": 1}

@app.get("/orders/{order_id}", tags=["Orders"])
async def get_order_detail(product_id: int):
    return {"user_id": 1}

@app.post("/orders/", tags=["Orders"])
async def create_order():
    return {"message": "Заказ создан"}

@app.put("/orders/{order_id}", tags=["Orders"])
async def update_order(product_id: int):
    return {"message": "Заказ обновлен"}

@app.delete("/orders/{order_id}", tags=["Orders"])
async def delete_order(product_id: int):
    return {"message": "Заказ удалён"}



