from pydantic import BaseModel, Field
from typing import Optional

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int

    class Config:
        orm_mode = True

class ProductBase(BaseModel):
    name: str
    price: float = Field(gt=0)
    category_id: int

class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    name: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    category_id: Optional[int] = None

class Product(ProductBase):
    id: int

    class Config:
        orm_mode = True 