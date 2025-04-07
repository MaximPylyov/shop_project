from fastapi import APIRouter, Depends, HTTPException
from database import  get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from  typing import List, Set
from uuid import UUID
import models, schemas
import uuid

router = APIRouter(prefix="/roles", tags=["Roles"])  

@router.get("/", response_model=List[schemas.Role])
async def get_roles(db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(
            select(models.Role).options(selectinload(models.Role.users))
        )
        roles = result.scalars().all()
        return roles

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Ошибка при отборе списка пользователей")

@router.post("/", response_model=schemas.Role)
async def create_role(role: schemas.RoleCreate, db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(
            select(models.Role).filter(models.Role.name == role.name)
        )
        db_role = result.scalar_one_or_none()
        if db_role:
            raise HTTPException(status_code=400, detail="Роль с таким названием уже есть")
        
        
        role_data = role.model_dump()
        role_data["id"] = uuid.uuid4()
        db_role = models.Role(**role_data)
        
        db.add(db_role)
        await db.commit()
        await db.refresh(db_role, ["users"])
        return db_role
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при создании роли {e}")


@router.put("/{role_id}", response_model=schemas.Role)
async def edit_role(role_id: UUID, role: schemas.RoleUpdate, db: AsyncSession = Depends(get_session)):
    try:
        if role.name:
            existing_role = await db.execute(
                select(models.Role).filter(
                    models.Role.name == role.name,
                    models.Role.id != role_id
                )
            )
            if existing_role.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Роль с таким названием уже существует")
        
        result = await db.execute(
            select(models.Role)
            .options(selectinload(models.Role.users))
            .filter(models.Role.id == role_id)
        )
        db_role = result.scalar_one_or_none()
        
        if not db_role:
            raise HTTPException(status_code=404, detail="Указанная роль не найдена")
        
        role_data = role.model_dump(exclude_unset=True)
        for field, value in role_data.items():
            setattr(db_role, field, value)
        
        await db.commit()
        await db.refresh(db_role)
        return db_role
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении роли {e}")

@router.delete("/{role_id}")
async def delete_role(role_id: UUID,  db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(
            select(models.Role)
            .options(selectinload(models.Role.users))
            .filter(models.Role.id == role_id)
        )
        db_role = result.scalar_one_or_none()
        
        if not db_role:
            raise HTTPException(status_code=404, detail="Указанная роль не найдена")
            
        if db_role.users:
            raise HTTPException(
                status_code=400, 
                detail="Невозможно удалить роль, так как есть связанные пользователи"
            )
        
        await db.delete(db_role)
        await db.commit()
        return {"message": "Роль удалена"} 

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка базы данных при удалении роли {e}")


@router.post("/add/{role_id}/users/{user_id}") 
async def assign_role(user_id: UUID, role_id: UUID, db: AsyncSession = Depends(get_session)):
    try:
        stmt = select(models.User).options(selectinload(models.User.roles)).where(models.User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        stmt = select(models.Role).where(models.Role.id == role_id)
        result = await db.execute(stmt)
        role = result.scalar_one_or_none()
        
        if not role:
            raise HTTPException(status_code=404, detail="Роль не найдена")
        
        if role in user.roles:
            raise HTTPException(status_code=400, detail="У пользователя уже есть эта роль")
        
        user_role = models.UserRole(
            id=uuid.uuid4(),
            user_id=user_id,
            role_id=role_id
        )
        db.add(user_role)
        await db.commit()
        
        return {"message": "Роль успешно назначена"}
    
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при назначении роли {e}")

@router.delete("/remove/{role_id}/users/{user_id}")
async def remove_role(user_id: UUID, role_id: UUID, db: AsyncSession = Depends(get_session)):
    try:
        stmt = select(models.User).options(selectinload(models.User.roles)).where(models.User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        stmt = select(models.Role).where(models.Role.id == role_id)
        result = await db.execute(stmt)
        role = result.scalar_one_or_none()
        
        if not role:
            raise HTTPException(status_code=404, detail="Роль не найдена")
        
        if role not in user.roles:
            raise HTTPException(status_code=400, detail="У пользователя нет этой роли")
        
        user.roles.remove(role)
        await db.commit()
        
        return {"message": "Роль успешно удалена"}
        
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении роли {e}")