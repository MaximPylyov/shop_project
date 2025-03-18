from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from tenacity import retry, stop_after_attempt, wait_exponential
import time
import os
from schemas import Product, ProductCreate, Category, CategoryCreate  

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



class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32))

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128))
    price = Column(Numeric(16,2))

    category_id = Column(Integer, ForeignKey("categories.id"))


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Catalog Service")

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


@app.get("/products/", tags=["Products"])
async def get_products():
    return {"name": "Товар 1", "price": 1200, "category_id": 1}

@app.get("/products/{product_id}", tags=["Products"])
async def get_product_detail(product_id: int):
    return {"name": "Товар 1", "price": 1200, "category_id": 1}

@app.post("/products/", tags=["Products"])
async def create_product():
    return {"message": "Товар создан"}

@app.put("/products/{product_id}", tags=["Products"])
async def update_product(product_id: int):
    return {"message": "Товар обновлен"}

@app.delete("/products/{product_id}", tags=["Products"])
async def delete_product(product_id: int):
    return {"message": "Товар удалён"}



@app.get("/categories/", tags=["Categories"])
async def get_categories():
    return {"name": "Категория 1"}

@app.get("/categories/{category_id}", tags=["Categories"])
async def get_category_detail(category_id: int):
    return {"name": "Категория 1"}

@app.post("/categories/", tags=["Categories"])
async def create_category():
    return {"message": "Категория создана"}

@app.put("/categories/{category_id}", tags=["Categories"])
async def update_category(category_id: int):
    return {"message": "Категория обновлена"}

@app.delete("/categories/{category_id}", tags=["Categories"])
async def delete_category(category_id: int):
    return {"message": "Категория удалена"}