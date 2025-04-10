import os
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

async def get_token_from_cookie(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не найден в cookie"
        )
    if token.startswith("Bearer "):
        token = token[7:]
    return token


async def get_current_roles(token: str = Depends(get_token_from_cookie)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("roles")
        if role is None:
            raise HTTPException(status_code=401, detail="Неверные учетные данные")
        return set(role)
    except JWTError:
        raise HTTPException(status_code=401, detail="Неверные учетные данные")

async def get_current_permissions(token: str = Depends(get_token_from_cookie)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        permissions = payload.get("permissions")
        if permissions is None:
            raise HTTPException(status_code=401, detail="Неверные учетные данные")
        return set(permissions)
    except JWTError:
        raise HTTPException(status_code=401, detail="Неверные учетные данные")



