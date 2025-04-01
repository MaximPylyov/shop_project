from tasks import celery_app, start_kafka_listener

if __name__ == '__main__':
    # Запускаем слушателя Kafka в отдельной задаче
    start_kafka_listener.delay()
