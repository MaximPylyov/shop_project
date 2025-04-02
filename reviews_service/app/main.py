from fastapi import FastAPI
from routes import router

app = FastAPI(title="Reviews Service")

app.include_router(router)


