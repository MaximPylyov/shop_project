from fastapi import APIRouter, Depends, HTTPException
from database import  get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from  typing import List, Set
from uuid import UUID
import models, schemas
import bcrypt
import uuid

from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[schemas.User])
async def get_users(db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(models.User).options(selectinload(models.User.roles))
    )
    users = result.scalars().all()
    return users

@router.post("/", response_model=schemas.User)
async def create_user(user: schemas.UserCreate,  db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(
            select(models.User).filter(models.User.email == user.email)
        )
        db_user = result.scalar_one_or_none()
        
        if db_user:
            raise HTTPException(status_code=400, detail="Пользователь с указаным email уже зарегистрирован")
        
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), salt)
        
        user_data = user.model_dump()
        user_data['hashed_password'] = hashed_password.decode('utf-8')
        user_data.pop('password', None)
        user_data['id'] = uuid.uuid4()
        
        db_user = models.User(**user_data)
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user, ["roles"])
        return db_user
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при создании пользователя: {e}")

@router.put("/{user_id}", response_model=schemas.User)
async def edit_user(user_id: UUID, user: schemas.UserUpdate, db: AsyncSession = Depends(get_session)):
    try:
        result = await db.execute(
            select(models.User)
            .options(selectinload(models.User.roles))
            .filter(models.User.id == user_id)
        )
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            raise HTTPException(status_code=404, detail="Указанный пользователь не найден")
        
        user_data = user.model_dump(exclude_unset=True)
        
        if 'password' in user_data:
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(user_data['password'].encode('utf-8'), salt)
            user_data['hashed_password'] = hashed_password.decode('utf-8')
            del user_data['password']
            
        for field, value in user_data.items():
            setattr(db_user, field, value)
        
        await db.commit()
        await db.refresh(db_user)
        return db_user
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при обновлении пользователя")

@router.delete("/{user_id}")
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_session)):
    try:

        result = await db.execute(
            select(models.User).filter(models.User.id == user_id)
        )
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            raise HTTPException(status_code=404, detail="Указанный пользователь не найден")
        
        await db.delete(db_user)
        await db.commit()
        return {"message": "Пользователь удалён"} 

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка базы данных при удалении пользователя")



@router.get("/{user_id}", response_model=schemas.User)
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_session)):
    
    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.roles))
        .filter(models.User.id == user_id)
    )
    db_user = result.scalar_one_or_none()

    return db_user