from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modelos.servicio import Servicio
    from app.modelos.tecnico import Tecnico


class ReprogramacionServicio(Base):
    __tablename__ = "reprogramaciones_servicio"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('PENDIENTE', 'APROBADA', 'RECHAZADA')",
            name="ck_reprogramaciones_servicio_estado",
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
    fecha_propuesta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(30), default="PENDIENTE", nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    servicio: Mapped[Servicio] = relationship(back_populates="reprogramaciones")
    tecnico: Mapped[Tecnico] = relationship(back_populates="reprogramaciones")
