import os
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from uuid import UUID
from logger import logger

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_access_token(data: dict) -> str:
    return create_token(
        data=data,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(data: dict) -> str:
    return create_token(
        data=data,
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_token_from_cookie(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        logger.warning("Попытка доступа без access_token в cookie", extra={"path": request.url.path, "client": request.client.host})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не найден в cookie"
        )
    logger.info(
        "Получен токен от пользователя",
        extra={"path": request.url.path, "client": request.client.host}
    )
    if token.startswith("Bearer "):
        token = token[7:]
    return token


async def get_current_user_id(token: str = Depends(get_token_from_cookie)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            logger.warning(
                "ID пользователя не найден в payload токена",
                extra={"payload_keys": list(payload.keys())}
            )
            raise HTTPException(status_code=401, detail="Неверные учетные данные")
        logger.info(
            "Успешно получен ID пользователя из токена",
            extra={"user_id": str(user_id)}
        )
        return UUID(user_id)
    except JWTError as e:
        logger.warning(
            "Ошибка декодирования JWT токена при получении ID пользователя",
            extra={"error": str(e)}
        )
        raise HTTPException(status_code=401, detail="Неверные учетные данные")
    except ValueError as e:
        logger.warning(
            "Некорректный формат ID пользователя в токене",
            extra={"user_id": user_id, "error": str(e)}
        )
        raise HTTPException(status_code=401, detail="Некорректный формат ID пользователя")

async def get_current_roles(token: str = Depends(get_token_from_cookie)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("roles")
        if role is None:
            logger.warning(
                "Роль не найдена в payload токена",
                extra={"payload_keys": list(payload.keys())}
            )
            raise HTTPException(status_code=401, detail="Неверные учетные данные")
        return set(role)
    except JWTError as e:
        logger.warning(
            "Ошибка декодирования JWT токена",
            extra={"error": str(e)}
        )
        raise HTTPException(status_code=401, detail="Неверные учетные данные")

async def get_current_permissions(token: str = Depends(get_token_from_cookie)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        permissions = payload.get("permissions")
        if permissions is None:
            logger.warning(
                "Доступы не найдены в payload токена",
                extra={"payload_keys": list(payload.keys())}
            )
            raise HTTPException(status_code=401, detail="Неверные учетные данные")
        return set(permissions)
    except JWTError as e:
        logger.warning(
            "Ошибка декодирования JWT токена",
            extra={"error": str(e)}
        )
        raise HTTPException(status_code=401, detail="Неверные учетные данные")
