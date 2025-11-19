from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes_auth import router as auth_router
from app.api.v1.routes_files import router as files_router
from app.api.v1.routes_users import router as users_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging


settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # ここで将来的に DB 接続確認やキャッシュウォームアップを実行できる
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        openapi_url=f"{settings.api_v1_str}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_router = APIRouter()
    api_router.include_router(auth_router)
    api_router.include_router(users_router)
    api_router.include_router(files_router)

    application.include_router(api_router, prefix=settings.api_v1_str)

    @application.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok"}

    return application


app = create_app()


