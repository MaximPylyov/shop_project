from fastapi import FastAPI
from database import  wait_for_db  # Импортируем необходимые функции и классы
from routes import router

app = FastAPI(title="Orders Service")

@app.on_event("startup")
async def startup():
    app.state.db = await wait_for_db()

app.include_router(router)


