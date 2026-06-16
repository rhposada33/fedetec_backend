from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.propina_servicio import PropinaServicio


class PropinaDuplicadaError(ValueError):
    pass


class PropinaServicioRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def obtener_por_servicio(self, servicio_id: UUID) -> PropinaServicio | None:
        stmt = select(PropinaServicio).where(PropinaServicio.servicio_id == servicio_id)
        return await self.session.scalar(stmt)

    async def crear(self, propina: PropinaServicio) -> PropinaServicio:
        self.session.add(propina)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise PropinaDuplicadaError("El servicio ya tiene propina registrada") from exc
        return propina
