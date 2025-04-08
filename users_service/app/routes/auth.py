from fastapi import APIRouter, Depends, Response, HTTPException, Cookie
from database import  get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_
from  typing import List, Set
from uuid import UUID
import models
from auth_services import create_access_token, create_refresh_token, verify_token
from auth_services import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from schemas import UserLogin
import bcrypt

from fastapi import APIRouter



router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
async def login(creds: UserLogin, response: Response, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.roles).selectinload(models.Role.permissions))
        .filter(
            and_(
                models.User.email == creds.email,
            )
        )
    )
    db_user = result.scalar_one_or_none()

    if db_user is None:
        raise HTTPException(status_code=401, detail="Неправильная почта или пароль (или пользователь не существует)")

    is_valid = bcrypt.checkpw(creds.password.encode('utf-8'), db_user.hashed_password.encode('utf-8'))

    if is_valid:
        user_roles = db_user.roles

        user_permissions = [permission for role in user_roles for permission in role.permissions]

        token_data = {
            "sub": str(db_user.id),
            "roles": [role.name for role in user_roles],  
            "permissions": [permission.name for permission in user_permissions],  
            "email": db_user.email
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token({"sub": str(db_user.id)})
        
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
        
        return {"message": "Вы успешно авторизовались"}
    else:
        raise HTTPException(status_code=401, detail="Неправильная почта или пароль (или пользователь не существует)")

@router.post("/refresh")
async def refresh_tokens(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_session)
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Отсутствует refresh token")
        
    payload = verify_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный refresh token")
        
    user_id = payload.get("sub")
    result = await db.execute(
        select(models.User)
        .options(selectinload(models.User.roles).selectinload(models.Role.permissions))
        .filter(models.User.id == UUID(user_id))
    )
    
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    token_data = {
        "sub": str(db_user.id),
        "roles": [role.name for role in db_user.roles],
        "permissions": [p.name for role in db_user.roles for p in role.permissions],
        "email": db_user.email
    }
    
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token({"sub": str(db_user.id)})
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {new_access_token}",
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return {"message": "Токены успешно обновлены"}