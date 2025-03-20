from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
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