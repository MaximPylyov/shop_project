from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from database import wait_for_db  # Импортируем необходимые функции и классы
from routes import router

app = FastAPI(
    title="Orders Service",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": "your-client-id"
    }
)

# Определяем схему OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.on_event("startup")
async def startup():
    app.state.db = await wait_for_db()

app.include_router(router)


