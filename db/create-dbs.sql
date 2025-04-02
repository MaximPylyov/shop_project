SELECT 'CREATE DATABASE catalog_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'catalog_db')\gexec
SELECT 'CREATE DATABASE orders_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'orders_db')\gexec
SELECT 'CREATE DATABASE celery_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'celery_db')\gexec
