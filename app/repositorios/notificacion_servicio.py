from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.notificacion_servicio import NotificacionServicio


class NotificacionServicioRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def crear_para_tecnicos_una_vez(
        self, servicio_id: UUID, tecnico_ids: list[UUID]
    ) -> int:
        if not tecnico_ids:
            return 0

        stmt = (
            insert(NotificacionServicio)
            .values(
                [
                    {
                        "servicio_id": servicio_id,
                        "tecnico_id": tecnico_id,
                        "estado": "ENVIADA",
                    }
                    for tecnico_id in tecnico_ids
                ]
            )
            .on_conflict_do_nothing(
                constraint="uq_notificaciones_servicio_servicio_id_tecnico_id"
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0
