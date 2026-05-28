from datetime import datetime
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Sede(Base):
    __tablename__ = "sedes"
    __table_args__ = (Index("idx_sedes_ubicacion", "ubicacion", postgresql_using="gist"),)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    nombre: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    direccion: Mapped[str | None] = mapped_column(Text)
    ubicacion: Mapped[str | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
