from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConfiguracionApp(Base):
    __tablename__ = "configuracion_app"

    clave: Mapped[str] = mapped_column(String(100), primary_key=True)
    valor: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
