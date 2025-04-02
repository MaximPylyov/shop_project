\c orders_db

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id integer,
    status varchar(16),
    total_price numeric(32,2),
    shipping_cost numeric(32,2) DEFAULT NULL,
    tracking_number varchar(16) DEFAULT NULL,
    created_at timestamp,
    updated_at timestamp
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE ON UPDATE CASCADE,
    product_id INTEGER,
    quantity INTEGER,
    price_at_moment numeric(16,2)
);