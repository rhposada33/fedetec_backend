from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminDep, SesionDep
from app.schemas.evidencia_servicio import EvidenciaServicioLeer
from app.servicios.evidencia_servicio import EvidenciaServicioServicio

router = APIRouter()


@router.post("/{evidencia_id}/aprobar", response_model=EvidenciaServicioLeer)
async def aprobar_evidencia(
    evidencia_id: UUID, session: SesionDep, admin: AdminDep
) -> EvidenciaServicioLeer:
    evidencia = await EvidenciaServicioServicio(session).aprobar(evidencia_id, admin)
    if evidencia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada",
        )
    return evidencia


@router.post("/{evidencia_id}/rechazar", response_model=EvidenciaServicioLeer)
async def rechazar_evidencia(
    evidencia_id: UUID, session: SesionDep, admin: AdminDep
) -> EvidenciaServicioLeer:
    evidencia = await EvidenciaServicioServicio(session).rechazar(evidencia_id, admin)
    if evidencia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada",
        )
    return evidencia
