from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modelos.calificacion_servicio import CalificacionServicio
    from app.modelos.empresa_cliente import EmpresaCliente
    from app.modelos.evidencia_servicio import EvidenciaServicio
    from app.modelos.notificacion_servicio import NotificacionServicio
    from app.modelos.rechazo_servicio import RechazoServicio
    from app.modelos.reporte_pago import ReportePago
    from app.modelos.reprogramacion_servicio import ReprogramacionServicio
    from app.modelos.tecnico import Tecnico


class Servicio(Base):
    __tablename__ = "servicios"
    __table_args__ = (
        CheckConstraint("tipo_servicio IN (1, 2, 3)", name="ck_servicios_tipo_servicio"),
        CheckConstraint(
            "estado IN ('CREADO', 'DISPONIBLE', 'ACEPTADO', 'EN_PROCESO', 'FINALIZADO', "
            "'VALIDADO', 'PAGO_GENERADO', 'RECHAZADO', 'REPROGRAMACION_SOLICITADA', "
            "'CANCELADO')",
            name="ck_servicios_estado",
        ),
        UniqueConstraint(
            "empresa_cliente_id",
            "clave_idempotencia",
            name="uq_servicios_empresa_cliente_id_clave_idempotencia",
        ),
        Index("ix_servicios_estado", "estado"),
        Index("idx_servicios_ubicacion", "ubicacion", postgresql_using="gist"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    empresa_cliente_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("empresas_cliente.id"), nullable=False
    )
    tipo_servicio: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    placa_vehiculo: Mapped[str | None] = mapped_column(String(30))
    ubicacion: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    direccion: Mapped[str | None] = mapped_column(Text)
    fecha_programada: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(50), default="CREADO", nullable=False)
    tecnico_aceptado_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tecnicos.id")
    )
    fecha_aceptacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_finalizacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_validacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_pago_generado: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clave_idempotencia: Mapped[str] = mapped_column(String(150), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    empresa_cliente: Mapped[EmpresaCliente] = relationship(back_populates="servicios")
    tecnico_aceptado: Mapped[Tecnico | None] = relationship(back_populates="servicios_aceptados")
    notificaciones: Mapped[list[NotificacionServicio]] = relationship(back_populates="servicio")
    rechazos: Mapped[list[RechazoServicio]] = relationship(back_populates="servicio")
    reprogramaciones: Mapped[list[ReprogramacionServicio]] = relationship(back_populates="servicio")
    evidencias: Mapped[list[EvidenciaServicio]] = relationship(back_populates="servicio")
    reporte_pago: Mapped[ReportePago | None] = relationship(
        back_populates="servicio", uselist=False
    )
    calificacion: Mapped[CalificacionServicio | None] = relationship(
        back_populates="servicio", uselist=False
    )
