from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CalificacionServicioCrear(BaseModel):
    puntuacion: int = Field(ge=1, le=5)
    comentario: str | None = None


class CalificacionServicioLeer(BaseModel):
    id: UUID
    servicio_id: UUID
    empresa_cliente_id: UUID
    tecnico_id: UUID
    puntuacion: int
    comentario: str | None = None
    fecha_calificacion: datetime
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)
