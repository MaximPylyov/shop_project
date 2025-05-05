from multiprocessing import Process

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uvicorn
from prometheus_fastapi_instrumentator import Instrumentator

from database import wait_for_db, get_session
from models import ExchangeRate
from tasks import start_kafka_listener
from logger import logger

app = FastAPI(title="Celery Worker API")

Instrumentator().instrument(app).expose(app)

@app.on_event("startup")
async def startup():
    logger.info("Celery Worker API startup")
    app.state.db = await wait_for_db()

@app.on_event("shutdown")
async def shutdown():
    logger.info("Celery Worker API shutdown")

@app.get("/exchange-rates/latest")
async def get_latest_rate(db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(ExchangeRate)
        .order_by(ExchangeRate.created_at.desc())
        .limit(1)
    )
    rate = result.scalar_one_or_none()
    if not rate:
        logger.warning("Курс обмена не найден")
        raise HTTPException(status_code=404, detail="Курс обмена не найден")

    logger.info("Вернули курс обмена из БД", extra={"rate": rate.rate})
    return {"rate": rate.rate}

def run_kafka_listener():
    start_kafka_listener.delay()

def start_api():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
