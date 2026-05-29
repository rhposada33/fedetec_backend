from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.calificacion_servicio import CalificacionServicio


class CalificacionDuplicadaError(ValueError):
    pass


class CalificacionServicioRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def obtener_por_servicio(self, servicio_id: UUID) -> CalificacionServicio | None:
        stmt = select(CalificacionServicio).where(CalificacionServicio.servicio_id == servicio_id)
        return await self.session.scalar(stmt)

    async def crear(self, calificacion: CalificacionServicio) -> CalificacionServicio:
        self.session.add(calificacion)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise CalificacionDuplicadaError("El servicio ya fue calificado") from exc

        await self.session.refresh(calificacion)
        return calificacion
