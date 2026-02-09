from fastapi import FastAPI
from fastapi.routing import APIRouter

from app.models import prisma
from app.routers import auth


def create_app() -> FastAPI:
    app = FastAPI(
        title="CRM Backend",
        version="0.1.0",
    )

    api_router = APIRouter()
    api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

    app.include_router(api_router, prefix="/api")

    @app.get("/")
    async def root() -> dict:
        return {"status": "ok"}

    @app.on_event("startup")
    async def on_startup() -> None:
        await prisma.connect()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await prisma.disconnect()

    return app


app = create_app()
