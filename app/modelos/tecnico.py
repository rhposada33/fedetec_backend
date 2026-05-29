from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modelos.calificacion_servicio import CalificacionServicio
    from app.modelos.notificacion_servicio import NotificacionServicio
    from app.modelos.rechazo_servicio import RechazoServicio
    from app.modelos.reporte_pago import ReportePago
    from app.modelos.reprogramacion_servicio import ReprogramacionServicio
    from app.modelos.servicio import Servicio
    from app.modelos.usuario import Usuario


class Tecnico(Base):
    __tablename__ = "tecnicos"
    __table_args__ = (
        Index("idx_tecnicos_ubicacion_actual", "ubicacion_actual", postgresql_using="gist"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), unique=True, nullable=False
    )
    ubicacion_actual: Mapped[str | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    esta_disponible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_ultima_ubicacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    usuario: Mapped[Usuario] = relationship(back_populates="tecnico")
    servicios_aceptados: Mapped[list[Servicio]] = relationship(back_populates="tecnico_aceptado")
    notificaciones: Mapped[list[NotificacionServicio]] = relationship(back_populates="tecnico")
    rechazos: Mapped[list[RechazoServicio]] = relationship(back_populates="tecnico")
    reprogramaciones: Mapped[list[ReprogramacionServicio]] = relationship(back_populates="tecnico")
    reportes_pago: Mapped[list[ReportePago]] = relationship(back_populates="tecnico")
    calificaciones: Mapped[list[CalificacionServicio]] = relationship(back_populates="tecnico")
