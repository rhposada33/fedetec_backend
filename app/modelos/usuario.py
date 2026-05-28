from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modelos.empresa_cliente import EmpresaCliente
    from app.modelos.evidencia_servicio import EvidenciaServicio
    from app.modelos.tecnico import Tecnico
    from app.modelos.usuario_rol import UsuarioRol


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    nombre_completo: Mapped[str] = mapped_column(String(150), nullable=False)
    correo: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    hash_contrasena: Mapped[str] = mapped_column(Text, nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(50))
    numero_documento: Mapped[str | None] = mapped_column(String(50))
    ciudad: Mapped[str | None] = mapped_column(String(100))
    municipio: Mapped[str | None] = mapped_column(String(100))
    direccion: Mapped[str | None] = mapped_column(Text)
    eps: Mapped[str | None] = mapped_column(String(100))
    arl: Mapped[str | None] = mapped_column(String(100))
    tiene_vehiculo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    placa_vehiculo: Mapped[str | None] = mapped_column(String(30))
    esta_activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    roles: Mapped[list[UsuarioRol]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )
    tecnico: Mapped[Tecnico | None] = relationship(back_populates="usuario", uselist=False)
    empresa_cliente: Mapped[EmpresaCliente | None] = relationship(
        back_populates="usuario", uselist=False
    )
    evidencias_subidas: Mapped[list[EvidenciaServicio]] = relationship(
        back_populates="subido_por_usuario",
        foreign_keys="EvidenciaServicio.subido_por_usuario_id",
    )
    evidencias_aprobadas: Mapped[list[EvidenciaServicio]] = relationship(
        back_populates="aprobado_por_usuario",
        foreign_keys="EvidenciaServicio.aprobado_por_usuario_id",
    )
