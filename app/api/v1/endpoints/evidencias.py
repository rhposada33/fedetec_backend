from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import EmpresaClienteActualDep, SesionDep, UsuarioActualDep
from app.schemas.evidencia_servicio import EvidenciaServicioLeer
from app.servicios.evidencia_servicio import EvidenciaServicioServicio

router = APIRouter()


@router.get("", response_model=list[EvidenciaServicioLeer])
async def listar_evidencias_empresa(
    session: SesionDep,
    empresa: EmpresaClienteActualDep,
    estado: str | None = Query(default=None, pattern="^(PENDIENTE|APROBADA|RECHAZADA)$"),
) -> list[EvidenciaServicioLeer]:
    return await EvidenciaServicioServicio(session).listar_por_empresa(empresa.id, estado)


@router.post("/{evidencia_id}/aprobar", response_model=EvidenciaServicioLeer)
async def aprobar_evidencia(
    evidencia_id: UUID, session: SesionDep, usuario: UsuarioActualDep
) -> EvidenciaServicioLeer:
    try:
        evidencia = await EvidenciaServicioServicio(session).aprobar(evidencia_id, usuario)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if evidencia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada",
        )
    return evidencia


@router.post("/{evidencia_id}/rechazar", response_model=EvidenciaServicioLeer)
async def rechazar_evidencia(
    evidencia_id: UUID, session: SesionDep, usuario: UsuarioActualDep
) -> EvidenciaServicioLeer:
    try:
        evidencia = await EvidenciaServicioServicio(session).rechazar(evidencia_id, usuario)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if evidencia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada",
        )
    return evidencia
