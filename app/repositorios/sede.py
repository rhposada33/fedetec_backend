from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.sede import Sede


class SedeRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def listar(self) -> list[Sede]:
        stmt = select(Sede).order_by(Sede.nombre)
        return list(await self.session.scalars(stmt))

    async def crear(self, sede: Sede) -> Sede:
        self.session.add(sede)
        await self.session.commit()
        await self.session.refresh(sede)
        return sede
