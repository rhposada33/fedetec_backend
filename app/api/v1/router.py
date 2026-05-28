from fastapi import APIRouter

from app.api.v1.endpoints import autenticacion, sedes, usuarios

api_router = APIRouter()
api_router.include_router(autenticacion.router, prefix="/autenticacion", tags=["autenticacion"])
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["usuarios"])
api_router.include_router(sedes.router, prefix="/sedes", tags=["sedes"])

