from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
from decimal import Decimal


KAFKA_URL = "kafka:9092"

def custom_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)  
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

async def send_event(event: dict):
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_URL,
        value_serializer=lambda v: json.dumps(v, default=custom_serializer).encode('utf-8')
    )
    await producer.start()
    
    try:
        await producer.send('order_events', value=event)
        print(f"Отправлено событие в Kafka: {event}")
    finally:
        await producer.stop()


async def consume_events():
    consumer = AIOKafkaConsumer(
        'order_events',
        bootstrap_servers=KAFKA_URL,
        group_id='my_group',
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )
    await consumer.start()
    
    try:
        async for message in consumer:
            event = message.value
            print(f"Получено событие: {event}")
    finally:
        await consumer.stop()