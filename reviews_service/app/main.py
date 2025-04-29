from fastapi import FastAPI
from routes import router
from prometheus_fastapi_instrumentator import Instrumentator
from logger import logger

def create_app():
    app = FastAPI(title="Reviews Service")
    @app.on_event("startup")
    async def startup():
        logger.info("Reviews Service startup")

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("Reviews Service shutdown")

    Instrumentator().instrument(app).expose(app)
    app.include_router(router)

    return app

app = create_app()
