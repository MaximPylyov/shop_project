FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ./app .

# Используем shell form чтобы запустить оба процесса
CMD celery -A tasks worker --beat -l info & python main.py