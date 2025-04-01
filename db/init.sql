--Catalog Service
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name varchar(32)
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name varchar(128),
    price numeric(16,2),
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL ON UPDATE CASCADE
);

--Orders Service

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
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE ON UPDATE CASCADE,
    quantity INTEGER,
    price_at_moment numeric(16,2)
);

CREATE TABLE IF NOT EXISTS exchange_rates (
    id SERIAL PRIMARY KEY,
    base_currency char(3),
    target_currency char(3),
    rate float,
    created_at timestamp
);
