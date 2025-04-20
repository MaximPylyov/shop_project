from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4

class ReviewCreate(BaseModel):
    product_id: int
    rating: int = Field(..., ge=1, le=5)  
    comment: str

class ReviewShow(BaseModel):
    id: str = Field(..., pattern="^[0-9a-f]{24}$")
    product_id: int
    user_id: UUID = Field(default_factory=uuid4)
    rating: int = Field(..., ge=1, le=5)  
    comment: str 
    created_at: datetime