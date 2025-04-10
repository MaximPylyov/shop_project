import asyncio
import json
import logging
import os
from datetime import datetime
from functools import wraps

import aioredis
import httpx
import redis.asyncio as redis
from aiokafka import AIOKafkaConsumer
from celery import Celery
from celery.schedules import crontab
from celery.signals import task_prerun, task_postrun, task_failure, worker_ready
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models import Base, ExchangeRate

celery_app = Celery('tasks')
celery_app.conf.broker_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
celery_app.conf.result_backend = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')

celery_app.conf.update(
    broker_connection_retry=True,
    broker_connection_max_retries=None,
    task_acks_late=True,
    task_reject_on_worker_lost=True
)

celery_app.conf.beat_schedule = {
    'fetch-exchange-rates': {
        'task': 'tasks.fetch_exchange_rates',
        'schedule': crontab(minute=0),
    },
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def log_task_execution(task_func):
    @wraps(task_func)
    def wrapper(*args, **kwargs):
        try:
            logger.info(f"Starting task {task_func.__name__}")
            result = task_func(*args, **kwargs)
            logger.info(f"Task {task_func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Task {task_func.__name__} failed: {str(e)}", exc_info=True)
            raise
    return wrapper


@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    logger.info(f"Task {task.name}[{task_id}] is about to run")

@task_postrun.connect
def task_postrun_handler(task_id, task, *args, retval=None, state=None, **kwargs):
    logger.info(f"Task {task.name}[{task_id}] finished with state: {state}")

@task_failure.connect
def task_failure_handler(task_id, exception, traceback, einfo, *args, **kwargs):
    logger.error(f"Task {task_id} failed: {str(exception)}", exc_info=True)

@celery_app.task
@log_task_execution
def fetch_exchange_rates():
    async def _fetch():
        engine = create_async_engine(os.getenv('DATABASE_URL'))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        redis_client = await aioredis.from_url(
            os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
            max_connections=10
        )
        
        try:
            async with httpx.AsyncClient() as client:
                FIXER_ACCESS_KEY = os.getenv('FIXER_ACCESS_KEY')
                response = await client.get(f'https://data.fixer.io/api/latest?access_key={FIXER_ACCESS_KEY}&format=1&symbols=RUB')
                data = response.json()
                
                if not data.get('success'):
                    raise ValueError("API вернул ошибку")
                    
                if 'rates' not in data or 'RUB' not in data['rates']:
                    raise ValueError("Отсутствуют данные о курсе RUB")
                
                await redis_client.setex('exchange_rates', 300, str(data['rates']['RUB']))
                
                async with async_session() as session:
                    exchange_rate = ExchangeRate(
                        base_currency=data['base'],
                        target_currency='RUB',
                        rate=data['rates']['RUB'],
                        created_at=datetime.fromtimestamp(data['timestamp'])
                    )
                    session.add(exchange_rate)
                    await session.commit()
        finally:
            await redis_client.close()
            await engine.dispose()

    asyncio.run(_fetch())

@celery_app.task
@log_task_execution
def process_order_created(order_data):
    async def _process():
        try:
            logger.info(f"Processing order {order_data.get('order_id')}")
            shipping_cost = await calculate_shipping_cost(order_data)
            logger.info(f"Calculated shipping cost for order {order_data.get('order_id')}: {shipping_cost}")
            
            token = order_data.get('token', '')
            headers = {"Cookie": f"access_token={token}"}  # Используем полный токен как есть
            
            order_id = order_data.get('order_id')
            payload = {
                "status": "DELIVERY_CALCULATED",
                "shipping_cost": float(shipping_cost) 
            }

            urls = [
                "http://orders_service:8000",
                "http://localhost:8002",
                "http://host.docker.internal:8002"
            ]

            async with httpx.AsyncClient(timeout=10.0) as client:
                last_error = None
                for base_url in urls:
                    try:
                        url = f"{base_url}/orders/{order_id}"
                        logger.info(f"Trying to connect to {url}")
                        response = await client.put(url, json=payload, headers=headers)
                        response.raise_for_status()
                        logger.info(f"Successfully updated order at {url}")
                        return
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Failed to connect to {url}: {str(e)}")
                        continue

                raise Exception(f"Failed to update order status. Last error: {str(last_error)}")

        except Exception as e:
            logger.error(f"Error processing order {order_data.get('order_id')}: {str(e)}", exc_info=True)
            raise

    asyncio.run(_process())

async def calculate_shipping_cost(order_data):
    return 70

async def start_kafka_consumer():
    while True:
        try:
            logger.info("Attempting to connect to Kafka...")
            consumer = AIOKafkaConsumer(
                'order_events',
                bootstrap_servers='kafka:9092',
                group_id='order_processor_group',
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
            await consumer.start()
            logger.info("Kafka consumer started successfully")
            
            async for msg in consumer:
                try:
                    event_data = json.loads(msg.value.decode())
                    logger.info(f"Received Kafka message: {event_data}")
                    
                    if event_data.get('action') == 'ORDER_CREATED':
                        logger.info(f"Processing ORDER_CREATED event for order_id: {event_data.get('order_id')}")
                        process_order_created.delay(event_data)
                except Exception as e:
                    logger.error(f"Error processing Kafka message: {e}")
        except Exception as e:
            logger.error(f"Kafka connection error: {e}")
            await asyncio.sleep(5) 

@celery_app.task(name='start_kafka_listener')
@log_task_execution
def start_kafka_listener():
    asyncio.run(start_kafka_consumer())

@worker_ready.connect
def at_worker_ready(sender, **kwargs):
    logger.info("Worker is ready, starting Kafka consumer...")
    start_kafka_listener.delay()
