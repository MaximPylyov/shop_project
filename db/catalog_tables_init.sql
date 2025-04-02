\c catalog_db;

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