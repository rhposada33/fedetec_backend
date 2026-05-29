from datetime import datetime
from typing import NamedTuple
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import Select, cast, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modelos.calificacion_servicio import CalificacionServicio
from app.modelos.notificacion_servicio import NotificacionServicio
from app.modelos.servicio import Servicio
from app.modelos.tecnico import Tecnico


class ServicioConUbicacion(NamedTuple):
    servicio: Servicio
    latitud: float
    longitud: float


class ServicioDetalleTecnico(NamedTuple):
    servicio: Servicio
    latitud: float
    longitud: float
    distancia_metros: float | None
    notificado: bool


class ServicioListaTecnico(NamedTuple):
    servicio: Servicio
    latitud: float
    longitud: float
    distancia_metros: float | None
    calificacion: int | None


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

    async def obtener_detalle_para_tecnico(
        self, servicio_id: UUID, tecnico_id: UUID
    ) -> ServicioDetalleTecnico | None:
        ubicacion_geometry = cast(Servicio.ubicacion, Geometry)
        notificado = exists(
            select(NotificacionServicio.id)
            .where(NotificacionServicio.servicio_id == Servicio.id)
            .where(NotificacionServicio.tecnico_id == tecnico_id)
        )
        distancia = func.ST_Distance(Servicio.ubicacion, Tecnico.ubicacion_actual)
        stmt = (
            select(
                Servicio,
                func.ST_Y(ubicacion_geometry).label("latitud"),
                func.ST_X(ubicacion_geometry).label("longitud"),
                distancia.label("distancia_metros"),
                notificado.label("notificado"),
            )
            .select_from(Servicio)
            .join(Tecnico, Tecnico.id == tecnico_id)
            .options(selectinload(Servicio.empresa_cliente))
            .where(Servicio.id == servicio_id)
        )
        row = (await self.session.execute(stmt)).one_or_none()
        return ServicioDetalleTecnico(*row) if row else None

    async def listar_para_tecnico(
        self,
        tecnico_id: UUID,
        estado: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ServicioListaTecnico], int]:
        ubicacion_geometry = cast(Servicio.ubicacion, Geometry)
        distancia = func.ST_Distance(Servicio.ubicacion, Tecnico.ubicacion_actual)
        filtros = self._filtros_servicio_tecnico(
            tecnico_id, estado, fecha_desde, fecha_hasta
        )

        stmt = (
            select(
                Servicio,
                func.ST_Y(ubicacion_geometry).label("latitud"),
                func.ST_X(ubicacion_geometry).label("longitud"),
                distancia.label("distancia_metros"),
                CalificacionServicio.puntuacion.label("calificacion"),
            )
            .select_from(Servicio)
            .join(Tecnico, Tecnico.id == tecnico_id)
            .outerjoin(Servicio.calificacion)
            .where(*filtros)
            .order_by(Servicio.fecha_programada.desc(), Servicio.fecha_creacion.desc())
            .limit(limit)
            .offset(offset)
        )
        total_stmt = select(func.count(Servicio.id)).where(*filtros)

        rows = (await self.session.execute(stmt)).all()
        total = await self.session.scalar(total_stmt)
        return [ServicioListaTecnico(*row) for row in rows], int(total or 0)

    async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> Servicio | None:
        stmt = select(Servicio).where(Servicio.id == servicio_id).with_for_update()
        return await self.session.scalar(stmt)

    async def obtener_por_id_con_historial(self, servicio_id: UUID) -> Servicio | None:
        stmt = self._select_historial().where(Servicio.id == servicio_id)
        return await self.session.scalar(stmt)

    async def obtener_por_id_y_empresa_con_historial(
        self, servicio_id: UUID, empresa_cliente_id: UUID
    ) -> Servicio | None:
        stmt = (
            self._select_historial()
            .where(Servicio.id == servicio_id)
            .where(Servicio.empresa_cliente_id == empresa_cliente_id)
        )
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
    def _filtros_servicio_tecnico(
        tecnico_id: UUID,
        estado: str | None,
        fecha_desde: datetime | None,
        fecha_hasta: datetime | None,
    ):
        notificado = exists(
            select(NotificacionServicio.id)
            .where(NotificacionServicio.servicio_id == Servicio.id)
            .where(NotificacionServicio.tecnico_id == tecnico_id)
        )
        filtros = [
            or_(
                notificado,
                Servicio.tecnico_aceptado_id == tecnico_id,
            )
        ]
        if estado is not None:
            filtros.append(Servicio.estado == estado)
        if fecha_desde is not None:
            filtros.append(Servicio.fecha_programada >= fecha_desde)
        if fecha_hasta is not None:
            filtros.append(Servicio.fecha_programada <= fecha_hasta)
        return filtros

    @staticmethod
    def _select_historial():
        return select(Servicio).options(
            selectinload(Servicio.notificaciones),
            selectinload(Servicio.rechazos),
            selectinload(Servicio.reprogramaciones),
            selectinload(Servicio.evidencias),
            selectinload(Servicio.reporte_pago),
            selectinload(Servicio.calificacion),
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
