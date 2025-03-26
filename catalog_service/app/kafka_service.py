from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
from decimal import Decimal


KAFKA_URL = "kafka:9092"

def custom_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)  # Преобразуем Decimal в float
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

async def send_event(event: dict):
    # Инициализация продюсера
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_URL,
        value_serializer=lambda v: json.dumps(v, default=custom_serializer).encode('utf-8')
    )
    await producer.start()
    
    try:
        # Отправка в топик "main_topic"
        await producer.send('main_topic', value=event)
        print("Событие отправлено!")
    finally:
        await producer.stop()


async def consume_events():
    # Инициализация консьюмера
    consumer = AIOKafkaConsumer(
        'main_topic',
        bootstrap_servers='localhost:9092',
        group_id='my_group',
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )
    await consumer.start()
    
    try:
        # Чтение событий
        async for message in consumer:
            event = message.value
            print(f"Получено событие: {event}")
            # Пример обработки: сохранение в БД
            # save_to_database(event)
    finally:
        await consumer.stop()