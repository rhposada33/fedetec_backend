from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings


def crear_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NOMBRE,
        debug=settings.DEBUG,
        version="0.1.0",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/salud", tags=["salud"])
    async def salud() -> dict[str, str]:
        return {"estado": "ok"}

    @app.get("/health", tags=["salud"])
    async def health() -> dict[str, str]:
        return {"estado": "ok"}

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = crear_app()
