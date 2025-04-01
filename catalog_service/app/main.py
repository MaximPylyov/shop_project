from fastapi import FastAPI
from database import wait_for_db
from routes import categories, products

app = FastAPI(title="Catalog Service")

@app.on_event("startup")
async def startup():
    app.state.db = await wait_for_db()

app.include_router(products.router)
app.include_router(categories.router)