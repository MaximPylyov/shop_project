from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from database import wait_for_db  
from routes import router
from prometheus_fastapi_instrumentator import Instrumentator

def create_app():
    app = FastAPI(
        title="Orders Service",
        swagger_ui_init_oauth={
            "usePkceWithAuthorizationCodeGrant": True,
            "clientId": "your-client-id"
        }
    )

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    @app.on_event("startup")
    async def startup():
        app.state.db = await wait_for_db()

    Instrumentator().instrument(app).expose(app)
    app.include_router(router)
    return app 

app = create_app()

