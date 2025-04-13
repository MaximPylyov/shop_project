from datetime import datetime
from typing import List, Set
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, Request
from sqlalchemy import and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth_services import (ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
                         create_access_token, create_refresh_token, verify_token)
from database import get_session
from kafka_service import send_event
from logger import logger
import models
from schemas import UserLogin

from fastapi import APIRouter


router = APIRouter(prefix="/auth", tags=["Auth"])

async def clear_access_token(response):
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=True,
        httponly=True,
        samesite="lax"
    )
    return response

async def clear_tokens(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=False,
        httponly=True,
        samesite="lax"
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        secure=False,
        httponly=True,
        samesite="lax"
    )
    return response

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
        logger.warning("Failed authorization attempt", extra={
            "service": "user_service",
            "email": creds.email
        })
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
        
        logger.info("User logged in", extra={
            "service": "user_service",
            "user_id": str(db_user.id),
            "email": creds.email
        })
        event = {
            "user_id": str(db_user.id),
            "email": creds.email,
            "action": "USER_LOGGED_IN",
            "timestamp": datetime.utcnow().isoformat()
        }
        await send_event(event)

        return {"message": "Вы успешно авторизовались"}
    else:
        logger.warning("Failed authorization attempt", extra={
            "service": "user_service",
            "email": creds.email
        })
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

@router.post("/logout")
async def logout(request: Request, response: Response):
    token = None
    auth_header = request.headers.get("Authorization")
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  
    else:
        token = request.cookies.get("access_token")  
        if token and token.startswith("Bearer "):
            token = token[7:]

    await clear_tokens(response)
    
    return {"message": "Успешный выход из системы"}