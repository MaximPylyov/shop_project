from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from uuid import UUID, uuid4

class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, description="Название роли не может быть пустым")

class RoleCreate(RoleBase):
    pass

class RoleUpdate(RoleBase):
    pass

class Role(RoleBase):
    id: UUID = Field(default_factory=uuid4)

    class Config:
        from_attributes = True


class PermissionBase(BaseModel):
    name: str = Field(..., min_length=1, description="Название доступа не может быть пустым")

class PermissionCreate(RoleBase):
    pass

class PermissionUpdate(RoleBase):
    pass

class Permission(RoleBase):
    id: UUID = Field(default_factory=uuid4)

    class Config:
        from_attributes = True



class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя", 
                          examples=["user@example.com"])

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя", 
                          examples=["user@example.com"])
    password: str

class User(UserBase):
    id: UUID = Field(default_factory=uuid4)
    email: EmailStr 