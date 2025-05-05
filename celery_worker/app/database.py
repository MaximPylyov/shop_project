import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession 
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy import text
from logger import logger

DATABASE_URL = os.getenv("DATABASE_URL")

Base = declarative_base()

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_db():
    engine = create_async_engine(DATABASE_URL, echo=True)
    return engine

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def wait_for_db():
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection successful!")
            return engine
        except Exception as e:
            logger.warning(
                "Database not ready",
                extra={"attempt": i + 1, "max_retries": max_retries, "error": str(e)}
            )
            if i < max_retries - 1:
                await asyncio.sleep(retry_interval)
        logger.error("Could not connect to database after retries", extra={"max_retries": max_retries})
    raise Exception("Could not connect to database") 

async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session