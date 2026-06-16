from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modelos.calificacion_servicio import CalificacionServicio
    from app.modelos.propina_servicio import PropinaServicio
    from app.modelos.reporte_pago import ReportePago
    from app.modelos.servicio import Servicio
    from app.modelos.usuario import Usuario


class EmpresaCliente(Base):
    __tablename__ = "empresas_cliente"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    identificacion_tributaria: Mapped[str | None] = mapped_column(String(80))
    correo_contacto: Mapped[str | None] = mapped_column(String(150))
    telefono_contacto: Mapped[str | None] = mapped_column(String(50))
    usuario_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), unique=True
    )
    hash_api_key: Mapped[str | None] = mapped_column(Text)
    esta_activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    servicios: Mapped[list[Servicio]] = relationship(back_populates="empresa_cliente")
    reportes_pago: Mapped[list[ReportePago]] = relationship(back_populates="empresa_cliente")
    calificaciones: Mapped[list[CalificacionServicio]] = relationship(
        back_populates="empresa_cliente"
    )
    propinas: Mapped[list[PropinaServicio]] = relationship(back_populates="empresa_cliente")
    usuario: Mapped[Usuario | None] = relationship(back_populates="empresa_cliente")
