from fastapi import FastAPI
from routes import router
from prometheus_fastapi_instrumentator import Instrumentator

def create_app():
    app = FastAPI(title="Reviews Service")
    Instrumentator().instrument(app).expose(app)
    app.include_router(router)

    return app

app = create_app()
