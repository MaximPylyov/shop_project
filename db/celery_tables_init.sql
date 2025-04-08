\c celery_db

CREATE TABLE IF NOT EXISTS exchange_rates (
    id SERIAL PRIMARY KEY,
    base_currency char(3),
    target_currency char(3),
    rate float,
    created_at timestamp
);
