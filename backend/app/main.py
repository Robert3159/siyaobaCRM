import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

from app.core.database import init_db, dispose_db
from app.core.exceptions import BusinessError, business_error_handler, validation_error_handler
from app.routers import auth, customer, menu, player, project, role, schema, user
from app.routers import notification_ws

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="CRM Backend",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:9527", "http://127.0.0.1:9527"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(BusinessError, business_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_, exc: Exception):
        logger.exception("未捕获异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误，请稍后重试",
                "msg": "服务器内部错误，请稍后重试",
            },
        )

    api_router = APIRouter()
    api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
    api_router.include_router(project.router, prefix="/projects", tags=["projects"])
    api_router.include_router(customer.router, prefix="/customers", tags=["customers"])
    api_router.include_router(schema.router, prefix="/schemas", tags=["schemas"])
    api_router.include_router(player.router, prefix="/players", tags=["players"])
    api_router.include_router(role.router, prefix="/system", tags=["system-role"])
    api_router.include_router(menu.router, prefix="/system", tags=["system-menu"])
    api_router.include_router(user.router, prefix="/users", tags=["system-user"])

    app.include_router(api_router, prefix="/api")
    app.include_router(notification_ws.router, prefix="/ws")

    @app.get("/")
    async def root() -> dict:
        return {"status": "ok"}

    @app.on_event("startup")
    async def on_startup() -> None:
        await init_db()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await dispose_db()

    return app


app = create_app()
