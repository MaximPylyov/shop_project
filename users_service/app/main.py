from fastapi import FastAPI
from database import  wait_for_db  # Импортируем необходимые функции и классы
from routes import auth, roles, users

app = FastAPI(title="User/Auth Service")

@app.on_event("startup")
async def startup():
    app.state.db = await wait_for_db()

app.include_router(auth.router)
app.include_router(roles.router)
app.include_router(users.router)