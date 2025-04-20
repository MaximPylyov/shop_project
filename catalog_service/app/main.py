from fastapi import FastAPI
from database import wait_for_db
from routes import categories, products
from prometheus_fastapi_instrumentator import Instrumentator

def create_app() -> FastAPI:
    app = FastAPI(title="Catalog Service")

    @app.on_event("startup")
    async def startup():
        app.state.db = await wait_for_db()

    Instrumentator().instrument(app).expose(app)

    app.include_router(products.router)
    app.include_router(categories.router)
    return app

app = create_app()
