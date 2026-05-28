from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modelos.servicio import Servicio
    from app.modelos.tecnico import Tecnico


class NotificacionServicio(Base):
    __tablename__ = "notificaciones_servicio"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('ENVIADA', 'LEIDA', 'ACEPTADA', 'RECHAZADA')",
            name="ck_notificaciones_servicio_estado",
        ),
        UniqueConstraint(
            "servicio_id", "tecnico_id", name="uq_notificaciones_servicio_servicio_id_tecnico_id"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    servicio_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("servicios.id"), nullable=False
    )
    tecnico_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tecnicos.id"), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(30), default="ENVIADA", nullable=False)
    fecha_envio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_lectura: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    servicio: Mapped[Servicio] = relationship(back_populates="notificaciones")
    tecnico: Mapped[Tecnico] = relationship(back_populates="notificaciones")
