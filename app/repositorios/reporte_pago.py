from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.reporte_pago import ReportePago


class ReportePagoDuplicadoError(ValueError):
    pass


class ReportePagoRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def listar(self) -> list[ReportePago]:
        stmt = select(ReportePago).order_by(ReportePago.fecha_generacion.desc())
        return list(await self.session.scalars(stmt))

    async def obtener_por_id(self, reporte_id: UUID) -> ReportePago | None:
        return await self.session.get(ReportePago, reporte_id)

    async def obtener_por_servicio_id(self, servicio_id: UUID) -> ReportePago | None:
        stmt = select(ReportePago).where(ReportePago.servicio_id == servicio_id)
        return await self.session.scalar(stmt)

    async def crear(self, reporte: ReportePago) -> ReportePago:
        self.session.add(reporte)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ReportePagoDuplicadoError(
                "Ya existe un reporte de pago para este servicio"
            ) from exc
        return reporte
