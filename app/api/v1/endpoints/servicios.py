from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.api.deps import AdminDep, EmpresaClienteApiKeyDep, SesionDep, TecnicoActualDep
from app.schemas.servicio import (
    ReprogramacionServicioLeer,
    ServicioCrear,
    ServicioLeer,
    ServicioPublicadoLeer,
    ServicioRechazadoLeer,
    ServicioRechazar,
    ServicioReprogramar,
)
from app.servicios.servicio import ServicioServicio

router = APIRouter()


@router.post("", response_model=ServicioLeer, status_code=status.HTTP_201_CREATED)
async def crear_servicio(
    servicio_in: ServicioCrear,
    session: SesionDep,
    empresa_cliente: EmpresaClienteApiKeyDep,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", max_length=150)
    ] = None,
) -> ServicioLeer:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header Idempotency-Key requerido",
        )

    return await ServicioServicio(session).crear(
        servicio_in, empresa_cliente, idempotency_key.strip()
    )


@router.get("", response_model=list[ServicioLeer])
async def listar_servicios(
    session: SesionDep, empresa_cliente: EmpresaClienteApiKeyDep
) -> list[ServicioLeer]:
    return await ServicioServicio(session).listar(empresa_cliente)


@router.get("/{servicio_id}", response_model=ServicioLeer)
async def obtener_servicio(
    servicio_id: UUID, session: SesionDep, empresa_cliente: EmpresaClienteApiKeyDep
) -> ServicioLeer:
    servicio = await ServicioServicio(session).obtener(servicio_id, empresa_cliente)
    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.post("/{servicio_id}/publicar", response_model=ServicioPublicadoLeer)
async def publicar_servicio(
    servicio_id: UUID,
    session: SesionDep,
    _admin: AdminDep,
    radio_metros: Annotated[int, Query(gt=0, le=100_000)] = 10_000,
) -> ServicioPublicadoLeer:
    try:
        servicio = await ServicioServicio(session).publicar(servicio_id, radio_metros)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.post("/{servicio_id}/aceptar", response_model=ServicioLeer)
async def aceptar_servicio(
    servicio_id: UUID,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> ServicioLeer:
    try:
        servicio = await ServicioServicio(session).aceptar(servicio_id, tecnico_actual)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.post("/{servicio_id}/rechazar", response_model=ServicioRechazadoLeer)
async def rechazar_servicio(
    servicio_id: UUID,
    rechazo_in: ServicioRechazar,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> ServicioRechazadoLeer:
    rechazo = await ServicioServicio(session).rechazar(servicio_id, tecnico_actual, rechazo_in)
    if rechazo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return rechazo


@router.post("/{servicio_id}/reprogramar", response_model=ReprogramacionServicioLeer)
async def reprogramar_servicio(
    servicio_id: UUID,
    reprogramacion_in: ServicioReprogramar,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> ReprogramacionServicioLeer:
    try:
        reprogramacion = await ServicioServicio(session).reprogramar(
            servicio_id, tecnico_actual, reprogramacion_in
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if reprogramacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return reprogramacion


@router.post("/{servicio_id}/iniciar", response_model=ServicioLeer)
async def iniciar_servicio(
    servicio_id: UUID,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> ServicioLeer:
    try:
        servicio = await ServicioServicio(session).iniciar(servicio_id, tecnico_actual)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.post("/{servicio_id}/finalizar", response_model=ServicioLeer)
async def finalizar_servicio(
    servicio_id: UUID,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> ServicioLeer:
    try:
        servicio = await ServicioServicio(session).finalizar(servicio_id, tecnico_actual)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio
