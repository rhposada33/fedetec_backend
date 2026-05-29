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
    from app.modelos.usuario import Usuario


class EvidenciaServicio(Base):
    __tablename__ = "evidencias_servicio"
    __table_args__ = (
        CheckConstraint(
            "estado_aprobacion IN ('PENDIENTE', 'APROBADA', 'RECHAZADA')",
            name="ck_evidencias_servicio_estado_aprobacion",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    servicio_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("servicios.id"), nullable=False
    )
    subido_por_usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    url_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(Text)
    tipo_archivo: Mapped[str | None] = mapped_column(String(50))
    descripcion: Mapped[str | None] = mapped_column(Text)
    estado_aprobacion: Mapped[str] = mapped_column(String(30), default="PENDIENTE", nullable=False)
    aprobado_por_usuario_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("usuarios.id")
    )
    fecha_aprobacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    servicio: Mapped[Servicio] = relationship(back_populates="evidencias")
    subido_por_usuario: Mapped[Usuario] = relationship(
        back_populates="evidencias_subidas",
        foreign_keys=[subido_por_usuario_id],
    )
    aprobado_por_usuario: Mapped[Usuario | None] = relationship(
        back_populates="evidencias_aprobadas",
        foreign_keys=[aprobado_por_usuario_id],
    )
