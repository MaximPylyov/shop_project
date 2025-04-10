from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    roles = relationship("Role", secondary="user_roles", back_populates="users")

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(UUID, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    users = relationship("User", secondary="user_roles", back_populates="roles")
    permissions = relationship("Permission", secondary="role_permissons", back_populates="roles")

class UserRole(Base):
    __tablename__ = "user_roles"
    
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"))
    role_id = Column(UUID, ForeignKey("roles.id"))

class Permission(Base):
    __tablename__ = "permissions"
    
    id = Column(UUID, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    roles = relationship("Role", secondary="role_permissons", back_populates="permissions")

class RolePermission(Base):
    __tablename__ = "role_permissons"
    
    id = Column(UUID, primary_key=True)
    role_id = Column(UUID, ForeignKey("roles.id"))
    permission_id = Column(UUID, ForeignKey("permissions.id"))

