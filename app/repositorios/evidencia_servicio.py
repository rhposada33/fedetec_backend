from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.evidencia_servicio import EvidenciaServicio


class EvidenciaServicioRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def listar_por_servicio(self, servicio_id: UUID) -> list[EvidenciaServicio]:
        stmt = (
            select(EvidenciaServicio)
            .where(EvidenciaServicio.servicio_id == servicio_id)
            .order_by(EvidenciaServicio.fecha_creacion.desc())
        )
        return list(await self.session.scalars(stmt))

    async def obtener_por_id(self, evidencia_id: UUID) -> EvidenciaServicio | None:
        return await self.session.get(EvidenciaServicio, evidencia_id)

    async def crear(self, evidencia: EvidenciaServicio) -> EvidenciaServicio:
        self.session.add(evidencia)
        await self.session.commit()
        await self.session.refresh(evidencia)
        return evidencia

    async def guardar(self, evidencia: EvidenciaServicio) -> EvidenciaServicio:
        await self.session.commit()
        await self.session.refresh(evidencia)
        return evidencia
