from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modelos.empresa_cliente import EmpresaCliente
    from app.modelos.servicio import Servicio
    from app.modelos.tecnico import Tecnico


class CalificacionServicio(Base):
    __tablename__ = "calificaciones_servicio"
    __table_args__ = (
        CheckConstraint("puntuacion BETWEEN 1 AND 5", name="ck_calificaciones_puntuacion"),
        UniqueConstraint("servicio_id", name="uq_calificaciones_servicio_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    servicio_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("servicios.id"), nullable=False
    )
    empresa_cliente_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("empresas_cliente.id"), nullable=False
    )
    tecnico_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tecnicos.id"), nullable=False
    )
    puntuacion: Mapped[int] = mapped_column(Integer, nullable=False)
    comentario: Mapped[str | None] = mapped_column(Text)
    fecha_calificacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    servicio: Mapped[Servicio] = relationship(back_populates="calificacion")
    empresa_cliente: Mapped[EmpresaCliente] = relationship(back_populates="calificaciones")
    tecnico: Mapped[Tecnico] = relationship(back_populates="calificaciones")
