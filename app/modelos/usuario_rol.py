from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modelos.rol import Rol
    from app.modelos.usuario import Usuario


class UsuarioRol(Base):
    __tablename__ = "usuario_roles"

    usuario_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("usuarios.id"), primary_key=True
    )
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)

    usuario: Mapped[Usuario] = relationship(back_populates="roles")
    rol: Mapped[Rol] = relationship(back_populates="usuarios")
