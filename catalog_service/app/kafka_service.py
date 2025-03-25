from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

KAFKA_URL = "kafka:9092"
TOPIC = "main_topic"
async def get_producer() -> AIOKafkaProducer:
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_URL)
    await producer.start()
    return producer

async def send_message(message: str):
    producer = await get_producer()
    try:
        await producer.send(TOPIC, message.encode("utf-8"))
        print("ОТПРАВИЛ СООБЩЕНИЕ")
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")
    finally:
        await producer.stop()

async def consume() -> AIOKafkaConsumer:
    consumer = AIOKafkaConsumer(
        'main_topic',
        bootstrap_servers=KAFKA_URL,
        group_id='your_group_id'
    )
    await consumer.start()
    return consumer 