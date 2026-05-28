from typing import NamedTuple
from uuid import UUID

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos.tecnico import Tecnico


class TecnicoConUbicacion(NamedTuple):
    tecnico: Tecnico
    latitud: float | None
    longitud: float | None
    distancia_metros: float | None = None


class TecnicoRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def obtener_por_id(self, tecnico_id: UUID) -> TecnicoConUbicacion | None:
        stmt = self._select_con_ubicacion().where(Tecnico.id == tecnico_id)
        row = (await self.session.execute(stmt)).one_or_none()
        return TecnicoConUbicacion(*row) if row else None

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
