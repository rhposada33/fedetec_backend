from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modelos.empresa_cliente import EmpresaCliente
    from app.modelos.servicio import Servicio
    from app.modelos.tecnico import Tecnico


class ReportePago(Base):
    __tablename__ = "reportes_pago"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('PENDIENTE', 'GENERADO', 'PAGADO', 'ANULADO')",
            name="ck_reportes_pago_estado",
        ),
        UniqueConstraint("servicio_id", name="uq_reportes_pago_servicio_id"),
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
    empresa_cliente_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("empresas_cliente.id"), nullable=False
    )
    valor: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    valor_base: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    valor_propina: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    estado: Mapped[str] = mapped_column(String(30), default="PENDIENTE", nullable=False)
    fecha_generacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    servicio: Mapped[Servicio] = relationship(back_populates="reporte_pago")
    tecnico: Mapped[Tecnico] = relationship(back_populates="reportes_pago")
    empresa_cliente: Mapped[EmpresaCliente] = relationship(back_populates="reportes_pago")
