from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import SesionDep, TecnicoActualDep, UsuarioActualDep
from app.schemas.servicio import ServicioLeer
from app.schemas.tecnico import (
    DisponibilidadTecnicoActualizar,
    NotificacionServicioTecnicoLeer,
    TecnicoCercanoLeer,
    TecnicoLeer,
    UbicacionTecnicoActualizar,
)
from app.servicios.tecnico import TecnicoServicio

router = APIRouter()


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


@router.get("/cercanos", response_model=list[TecnicoCercanoLeer])
async def listar_tecnicos_cercanos(
    session: SesionDep,
    _usuario_actual: UsuarioActualDep,
    latitud: Annotated[float, Query(ge=-90, le=90)],
    longitud: Annotated[float, Query(ge=-180, le=180)],
    radio_metros: Annotated[int, Query(gt=0, le=100_000)] = 10_000,
) -> list[TecnicoCercanoLeer]:
    return await TecnicoServicio(session).buscar_cercanos(latitud, longitud, radio_metros)
