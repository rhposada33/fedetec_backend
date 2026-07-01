from datetime import UTC, date, datetime, time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SesionDep, TecnicoActualDep, UsuarioActualDep
from app.schemas.servicio import ServicioLeer
from app.schemas.tecnico import (
    DisponibilidadTecnicoActualizar,
    FcmTokenActualizar,
    MetricasRendimientoTecnicoLeer,
    NotificacionServicioTecnicoLeer,
    RankingTecnicoLeer,
    ServicioListaTecnicoLeer,
    ServicioTecnicoDetalleLeer,
    TecnicoCercanoLeer,
    TecnicoLeer,
    UbicacionTecnicoActualizar,
)
from app.servicios.tecnico import TecnicoServicio

router = APIRouter()


@router.put("/yo/fcm-token", status_code=status.HTTP_204_NO_CONTENT)
async def registrar_fcm_token(
    token_in: FcmTokenActualizar, session: SesionDep, tecnico_actual: TecnicoActualDep
) -> None:
    await TecnicoServicio(session).actualizar_fcm_token(tecnico_actual, token_in.token)


@router.post(
    "/yo/notificaciones/{notificacion_id}/recibida", status_code=status.HTTP_204_NO_CONTENT
)
async def confirmar_notificacion_recibida(
    notificacion_id: UUID, session: SesionDep, tecnico_actual: TecnicoActualDep
) -> None:
    if not await TecnicoServicio(session).confirmar_notificacion(tecnico_actual, notificacion_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada"
        )


@router.post("/yo/notificaciones/{notificacion_id}/leida", status_code=status.HTTP_204_NO_CONTENT)
async def confirmar_notificacion_leida(
    notificacion_id: UUID, session: SesionDep, tecnico_actual: TecnicoActualDep
) -> None:
    if not await TecnicoServicio(session).confirmar_notificacion(
        tecnico_actual, notificacion_id, leida=True
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada"
        )


@router.get("/yo", response_model=TecnicoLeer)
async def obtener_tecnico_actual(
    session: SesionDep, tecnico_actual: TecnicoActualDep
) -> TecnicoLeer:
    return await TecnicoServicio(session).obtener_yo(tecnico_actual)


@router.patch("/yo/ubicacion", response_model=TecnicoLeer)
async def actualizar_ubicacion_tecnico_actual(
    ubicacion_in: UbicacionTecnicoActualizar,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> TecnicoLeer:
    return await TecnicoServicio(session).actualizar_ubicacion(tecnico_actual, ubicacion_in)


@router.patch("/yo/disponibilidad", response_model=TecnicoLeer)
async def actualizar_disponibilidad_tecnico_actual(
    disponibilidad_in: DisponibilidadTecnicoActualizar,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> TecnicoLeer:
    return await TecnicoServicio(session).actualizar_disponibilidad(
        tecnico_actual, disponibilidad_in
    )


@router.get("/yo/servicios-disponibles", response_model=list[ServicioLeer])
async def listar_servicios_disponibles_tecnico_actual(
    session: SesionDep, tecnico_actual: TecnicoActualDep
) -> list[ServicioLeer]:
    return await TecnicoServicio(session).listar_servicios_disponibles(tecnico_actual)


@router.get("/yo/notificaciones", response_model=list[NotificacionServicioTecnicoLeer])
async def listar_notificaciones_tecnico_actual(
    session: SesionDep, tecnico_actual: TecnicoActualDep
) -> list[NotificacionServicioTecnicoLeer]:
    return await TecnicoServicio(session).listar_notificaciones(tecnico_actual)


@router.get("/yo/servicios", response_model=ServicioListaTecnicoLeer)
async def listar_servicios_tecnico_actual(
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
    estado: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: Annotated[int, Query(gt=0, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ServicioListaTecnicoLeer:
    fecha_desde_dt = (
        datetime.combine(fecha_desde, time.min, tzinfo=UTC) if fecha_desde else None
    )
    fecha_hasta_dt = (
        datetime.combine(fecha_hasta, time.max, tzinfo=UTC) if fecha_hasta else None
    )
    return await TecnicoServicio(session).listar_servicios_tecnico(
        tecnico_actual,
        estado=estado,
        fecha_desde=fecha_desde_dt,
        fecha_hasta=fecha_hasta_dt,
        limit=limit,
        offset=offset,
    )


@router.get("/yo/servicios/{servicio_id}", response_model=ServicioTecnicoDetalleLeer)
async def obtener_detalle_servicio_tecnico_actual(
    servicio_id: UUID,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> ServicioTecnicoDetalleLeer:
    try:
        servicio = await TecnicoServicio(session).obtener_detalle_servicio(
            tecnico_actual, servicio_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.get("/yo/metricas", response_model=MetricasRendimientoTecnicoLeer)
async def obtener_metricas_tecnico_actual(
    session: SesionDep, tecnico_actual: TecnicoActualDep
) -> MetricasRendimientoTecnicoLeer:
    metricas = await TecnicoServicio(session).obtener_metricas_rendimiento(tecnico_actual.id)
    if metricas is None:
        raise RuntimeError("No fue posible recuperar las metricas del tecnico actual")
    return metricas


@router.get("/yo/ranking", response_model=RankingTecnicoLeer)
async def obtener_ranking_tecnico_actual(
    session: SesionDep, tecnico_actual: TecnicoActualDep
) -> RankingTecnicoLeer:
    ranking = await TecnicoServicio(session).obtener_ranking_actual(tecnico_actual)
    if ranking is None:
        raise RuntimeError("No fue posible recuperar el ranking del tecnico actual")
    return ranking


@router.get("/cercanos", response_model=list[TecnicoCercanoLeer])
async def listar_tecnicos_cercanos(
    session: SesionDep,
    _usuario_actual: UsuarioActualDep,
    latitud: Annotated[float, Query(ge=-90, le=90)],
    longitud: Annotated[float, Query(ge=-180, le=180)],
    radio_metros: Annotated[int, Query(gt=0, le=100_000)] = 10_000,
) -> list[TecnicoCercanoLeer]:
    return await TecnicoServicio(session).buscar_cercanos(latitud, longitud, radio_metros)
