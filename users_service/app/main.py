from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import wait_for_db
from routes import auth, roles, users, permissions

app = FastAPI(title="User/Auth Service")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True, 
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.on_event("startup")
async def startup():
    app.state.db = await wait_for_db()

app.include_router(auth.router)
app.include_router(roles.router)
app.include_router(users.router)
app.include_router(permissions.router)