from fastapi import APIRouter

from app.api.v1.endpoints import (
    autenticacion,
    empresas_cliente,
    evidencias,
    sedes,
    servicios,
    tecnicos,
    usuarios,
)

api_router = APIRouter()
api_router.include_router(autenticacion.router, prefix="/autenticacion", tags=["autenticacion"])
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["usuarios"])
api_router.include_router(sedes.router, prefix="/sedes", tags=["sedes"])
api_router.include_router(
    empresas_cliente.router, prefix="/empresas-cliente", tags=["empresas-cliente"]
)
api_router.include_router(servicios.router, prefix="/servicios", tags=["servicios"])
api_router.include_router(evidencias.router, prefix="/evidencias", tags=["evidencias"])
api_router.include_router(tecnicos.router, prefix="/tecnicos", tags=["tecnicos"])
