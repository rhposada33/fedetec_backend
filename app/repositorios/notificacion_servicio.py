from typing import NamedTuple
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from app.modelos.notificacion_servicio import NotificacionServicio
from app.modelos.servicio import Servicio


class NotificacionServicioConUbicacion(NamedTuple):
    notificacion: NotificacionServicio
    latitud: float
    longitud: float


class NotificacionServicioRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def crear_para_tecnicos_una_vez(
        self, servicio_id: UUID, tecnico_ids: list[UUID]
    ) -> int:
        if not tecnico_ids:
            return 0

        stmt = (
            insert(NotificacionServicio)
            .values(
                [
                    {
                        "servicio_id": servicio_id,
                        "tecnico_id": tecnico_id,
                        "estado": "ENVIADA",
                    }
                    for tecnico_id in tecnico_ids
                ]
            )
            .on_conflict_do_nothing(
                constraint="uq_notificaciones_servicio_servicio_id_tecnico_id"
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def actualizar_estado_para_tecnico(
        self, servicio_id: UUID, tecnico_id: UUID, estado: str
    ) -> int:
        stmt = (
            update(NotificacionServicio)
            .where(NotificacionServicio.servicio_id == servicio_id)
            .where(NotificacionServicio.tecnico_id == tecnico_id)
            .values(estado=estado)
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def listar_para_tecnico(
        self, tecnico_id: UUID
    ) -> list[NotificacionServicioConUbicacion]:
        stmt = (
            self._select_con_servicio_ubicacion()
            .where(NotificacionServicio.tecnico_id == tecnico_id)
            .order_by(NotificacionServicio.fecha_envio.desc())
        )
        return [
            NotificacionServicioConUbicacion(*row)
            for row in (await self.session.execute(stmt)).all()
        ]

    async def listar_servicios_disponibles_para_tecnico(
        self, tecnico_id: UUID
    ) -> list[NotificacionServicioConUbicacion]:
        stmt = (
            self._select_con_servicio_ubicacion()
            .where(NotificacionServicio.tecnico_id == tecnico_id)
            .where(NotificacionServicio.estado.in_(["ENVIADA", "LEIDA"]))
            .where(Servicio.estado == "DISPONIBLE")
            .order_by(NotificacionServicio.fecha_envio.desc())
        )
        return [
            NotificacionServicioConUbicacion(*row)
            for row in (await self.session.execute(stmt)).all()
        ]

    @staticmethod
    def _select_con_servicio_ubicacion():
        ubicacion_geometry = cast(Servicio.ubicacion, Geometry)
        return (
            select(
                NotificacionServicio,
                func.ST_Y(ubicacion_geometry).label("latitud"),
                func.ST_X(ubicacion_geometry).label("longitud"),
            )
            .join(NotificacionServicio.servicio)
            .options(contains_eager(NotificacionServicio.servicio))
        )
