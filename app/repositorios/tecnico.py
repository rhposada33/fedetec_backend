from typing import NamedTuple
from uuid import UUID

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos.calificacion_servicio import CalificacionServicio
from app.modelos.rechazo_servicio import RechazoServicio
from app.modelos.servicio import Servicio
from app.modelos.tecnico import Tecnico


class TecnicoConUbicacion(NamedTuple):
    tecnico: Tecnico
    latitud: float | None
    longitud: float | None
    distancia_metros: float | None = None


class MetricasRendimientoTecnico(NamedTuple):
    calificacion_promedio: float | None
    servicios_completados: int
    servicios_aceptados: int
    servicios_rechazados: int


class TecnicoRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def obtener_por_id(self, tecnico_id: UUID) -> TecnicoConUbicacion | None:
        stmt = self._select_con_ubicacion().where(Tecnico.id == tecnico_id)
        row = (await self.session.execute(stmt)).one_or_none()
        return TecnicoConUbicacion(*row) if row else None

    async def listar_admin(self, esta_disponible: bool | None = None) -> list[TecnicoConUbicacion]:
        stmt = self._select_con_ubicacion().order_by(Tecnico.fecha_creacion.desc())
        if esta_disponible is not None:
            stmt = stmt.where(Tecnico.esta_disponible.is_(esta_disponible))
        return [TecnicoConUbicacion(*row) for row in (await self.session.execute(stmt)).all()]

    async def guardar(self, tecnico: Tecnico) -> Tecnico:
        await self.session.commit()
        await self.session.refresh(tecnico)
        return tecnico

    async def buscar_cercanos(
        self, latitud: float, longitud: float, radio_metros: int
    ) -> list[TecnicoConUbicacion]:
        punto = WKTElement(f"POINT({longitud} {latitud})", srid=4326)
        distancia = func.ST_Distance(Tecnico.ubicacion_actual, punto)
        stmt = (
            self._select_con_ubicacion(distancia.label("distancia_metros"))
            .where(Tecnico.esta_disponible.is_(True))
            .where(Tecnico.ubicacion_actual.is_not(None))
            .where(func.ST_DWithin(Tecnico.ubicacion_actual, punto, radio_metros))
            .order_by(distancia)
        )
        return [TecnicoConUbicacion(*row) for row in (await self.session.execute(stmt)).all()]

    async def obtener_metricas_rendimiento(
        self, tecnico_id: UUID
    ) -> MetricasRendimientoTecnico:
        servicios_aceptados = await self.session.scalar(
            select(func.count(Servicio.id)).where(Servicio.tecnico_aceptado_id == tecnico_id)
        )
        servicios_completados = await self.session.scalar(
            select(func.count(Servicio.id))
            .where(Servicio.tecnico_aceptado_id == tecnico_id)
            .where(Servicio.estado.in_(["FINALIZADO", "VALIDADO", "PAGO_GENERADO"]))
        )
        servicios_rechazados = await self.session.scalar(
            select(func.count(RechazoServicio.id)).where(RechazoServicio.tecnico_id == tecnico_id)
        )
        calificacion_promedio = await self.session.scalar(
            select(func.avg(CalificacionServicio.puntuacion)).where(
                CalificacionServicio.tecnico_id == tecnico_id
            )
        )
        return MetricasRendimientoTecnico(
            calificacion_promedio=(
                float(calificacion_promedio) if calificacion_promedio is not None else None
            ),
            servicios_completados=int(servicios_completados or 0),
            servicios_aceptados=int(servicios_aceptados or 0),
            servicios_rechazados=int(servicios_rechazados or 0),
        )

    @staticmethod
    def _select_con_ubicacion(distancia=None):
        ubicacion_geometry = cast(Tecnico.ubicacion_actual, Geometry)
        columnas = [
            Tecnico,
            func.ST_Y(ubicacion_geometry).label("latitud"),
            func.ST_X(ubicacion_geometry).label("longitud"),
        ]
        if distancia is not None:
            columnas.append(distancia)
        return select(*columnas).options(selectinload(Tecnico.usuario))
