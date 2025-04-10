from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class OrderSchema(BaseModel):
    id: int
    user_id: UUID
    status: str
    total_price: float
    shipping_cost: Optional[float] = None
    tracking_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True 

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    shipping_cost: Optional[float] = None
    tracking_number: Optional[str] = None



class Item(BaseModel):
    product_id: int
    quantity: int