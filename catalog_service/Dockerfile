FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app

# Добавляем скрипт для запуска
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]