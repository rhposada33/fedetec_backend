from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.rechazo_servicio import RechazoServicio


class RechazoServicioRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def crear_una_vez(
        self, servicio_id: UUID, tecnico_id: UUID, motivo: str | None = None
    ) -> bool:
        stmt = (
            insert(RechazoServicio)
            .values(servicio_id=servicio_id, tecnico_id=tecnico_id, motivo=motivo)
            .on_conflict_do_nothing(
                constraint="uq_rechazos_servicio_servicio_id_tecnico_id"
            )
        )
        result = await self.session.execute(stmt)
        return bool(result.rowcount)
