from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.tipo_servicio import TipoServicio


class TipoServicioRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def listar(self, solo_activos: bool = False) -> list[TipoServicio]:
        stmt = select(TipoServicio).order_by(TipoServicio.id)
        if solo_activos:
            stmt = stmt.where(TipoServicio.esta_activo.is_(True))
        return list(await self.session.scalars(stmt))

    async def obtener_por_id(self, tipo_servicio_id: int) -> TipoServicio | None:
        return await self.session.get(TipoServicio, tipo_servicio_id)

    async def crear(self, tipo_servicio: TipoServicio) -> TipoServicio:
        self.session.add(tipo_servicio)
        await self.session.commit()
        await self.session.refresh(tipo_servicio)
        return tipo_servicio

    async def guardar(self, tipo_servicio: TipoServicio) -> TipoServicio:
        await self.session.commit()
        await self.session.refresh(tipo_servicio)
        return tipo_servicio
