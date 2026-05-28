from datetime import datetime
from typing import NamedTuple
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import Select, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.servicio import Servicio


class ServicioConUbicacion(NamedTuple):
    servicio: Servicio
    latitud: float
    longitud: float


class ServicioRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def listar_por_empresa(self, empresa_cliente_id: UUID) -> list[ServicioConUbicacion]:
        stmt = (
            self._select_con_ubicacion()
            .where(Servicio.empresa_cliente_id == empresa_cliente_id)
            .order_by(Servicio.fecha_creacion.desc())
        )
        return [ServicioConUbicacion(*row) for row in (await self.session.execute(stmt)).all()]

    async def listar_admin(
        self,
        estado: str | None = None,
        empresa_cliente_id: UUID | None = None,
        tecnico_id: UUID | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[ServicioConUbicacion]:
        stmt = self._aplicar_filtros_servicio(
            self._select_con_ubicacion(),
            estado,
            empresa_cliente_id,
            tecnico_id,
            fecha_desde,
            fecha_hasta,
        ).order_by(Servicio.fecha_creacion.desc())
        return [ServicioConUbicacion(*row) for row in (await self.session.execute(stmt)).all()]

    async def contar_por_estado(
        self,
        estado: str | None = None,
        empresa_cliente_id: UUID | None = None,
        tecnico_id: UUID | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> dict[str, int]:
        stmt = self._aplicar_filtros_servicio(
            select(Servicio.estado, func.count(Servicio.id)),
            estado,
            empresa_cliente_id,
            tecnico_id,
            fecha_desde,
            fecha_hasta,
        ).group_by(Servicio.estado)
        return {estado: cantidad for estado, cantidad in (await self.session.execute(stmt)).all()}

    async def obtener_por_id_y_empresa(
        self, servicio_id: UUID, empresa_cliente_id: UUID
    ) -> ServicioConUbicacion | None:
        stmt = (
            self._select_con_ubicacion()
            .where(Servicio.id == servicio_id)
            .where(Servicio.empresa_cliente_id == empresa_cliente_id)
        )
        row = (await self.session.execute(stmt)).one_or_none()
        return ServicioConUbicacion(*row) if row else None

    async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion | None:
        stmt = self._select_con_ubicacion().where(Servicio.id == servicio_id)
        row = (await self.session.execute(stmt)).one_or_none()
        return ServicioConUbicacion(*row) if row else None

    async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> Servicio | None:
        stmt = select(Servicio).where(Servicio.id == servicio_id).with_for_update()
        return await self.session.scalar(stmt)

    async def obtener_por_idempotencia(
        self, empresa_cliente_id: UUID, clave_idempotencia: str
    ) -> ServicioConUbicacion | None:
        stmt = (
            self._select_con_ubicacion()
            .where(Servicio.empresa_cliente_id == empresa_cliente_id)
            .where(Servicio.clave_idempotencia == clave_idempotencia)
        )
        row = (await self.session.execute(stmt)).one_or_none()
        return ServicioConUbicacion(*row) if row else None

    async def crear(self, servicio: Servicio) -> Servicio:
        self.session.add(servicio)
        await self.session.commit()
        await self.session.refresh(servicio)
        return servicio

    async def guardar(self, servicio: Servicio) -> Servicio:
        await self.session.commit()
        await self.session.refresh(servicio)
        return servicio

    async def crear_idempotente(
        self, servicio: Servicio, clave_idempotencia: str
    ) -> ServicioConUbicacion:
        existente = await self.obtener_por_idempotencia(
            servicio.empresa_cliente_id, clave_idempotencia
        )
        if existente is not None:
            return existente

        try:
            servicio = await self.crear(servicio)
        except IntegrityError:
            await self.session.rollback()
            existente = await self.obtener_por_idempotencia(
                servicio.empresa_cliente_id, clave_idempotencia
            )
            if existente is not None:
                return existente
            raise

        creado = await self.obtener_por_id_y_empresa(servicio.id, servicio.empresa_cliente_id)
        if creado is None:
            raise RuntimeError("No fue posible recuperar el servicio creado")
        return creado

    @staticmethod
    def _select_con_ubicacion():
        ubicacion_geometry = cast(Servicio.ubicacion, Geometry)
        return select(
            Servicio,
            func.ST_Y(ubicacion_geometry).label("latitud"),
            func.ST_X(ubicacion_geometry).label("longitud"),
        )

    @staticmethod
    def _aplicar_filtros_servicio(
        stmt: Select,
        estado: str | None,
        empresa_cliente_id: UUID | None,
        tecnico_id: UUID | None,
        fecha_desde: datetime | None,
        fecha_hasta: datetime | None,
    ) -> Select:
        if estado is not None:
            stmt = stmt.where(Servicio.estado == estado)
        if empresa_cliente_id is not None:
            stmt = stmt.where(Servicio.empresa_cliente_id == empresa_cliente_id)
        if tecnico_id is not None:
            stmt = stmt.where(Servicio.tecnico_aceptado_id == tecnico_id)
        if fecha_desde is not None:
            stmt = stmt.where(Servicio.fecha_creacion >= fecha_desde)
        if fecha_hasta is not None:
            stmt = stmt.where(Servicio.fecha_creacion <= fecha_hasta)
        return stmt
