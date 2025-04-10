from multiprocessing import Process

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uvicorn

from database import wait_for_db, get_session
from models import ExchangeRate
from tasks import start_kafka_listener

app = FastAPI(title="Celery Worker API")

@app.on_event("startup")
async def startup():
    app.state.db = await wait_for_db()

@app.get("/exchange-rates/latest")
async def get_latest_rate(db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(ExchangeRate)
        .order_by(ExchangeRate.created_at.desc())
        .limit(1)
    )
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="Курс обмена не найден")

    return {"rate": rate.rate}

def run_kafka_listener():
    start_kafka_listener.delay()

def start_api():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == '__main__':
    # Запускаем FastAPI и Kafka listener в отдельных процессах
    api_process = Process(target=start_api)
    kafka_process = Process(target=run_kafka_listener)
    
    api_process.start()
    kafka_process.start()
    
    api_process.join()
    kafka_process.join()
