from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.reprogramacion_servicio import ReprogramacionServicio


class ReprogramacionServicioRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def crear(self, reprogramacion: ReprogramacionServicio) -> ReprogramacionServicio:
        self.session.add(reprogramacion)
        await self.session.flush()
        await self.session.refresh(reprogramacion)
        return reprogramacion
