from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from database import Base


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32))

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128))
    price = Column(Numeric(16,2))
    category_id = Column(Integer, ForeignKey("categories.id")) 


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    status = Column(String(16))
    total_price = Column(Numeric(32,2))
    tracking_number = Column(String(16))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price_at_moment = Column(Numeric(16,2))

    