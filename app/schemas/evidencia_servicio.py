from datetime import datetime
from uuid import UUID

from pydantic import AnyUrl, BaseModel, ConfigDict, Field


class EvidenciaServicioCrear(BaseModel):
    url_archivo: AnyUrl
    tipo_archivo: str | None = Field(default=None, max_length=50)
    descripcion: str | None = None


class EvidenciaServicioLeer(BaseModel):
    id: UUID
    servicio_id: UUID
    subido_por_usuario_id: UUID
    url_archivo: str
    tipo_archivo: str | None = None
    descripcion: str | None = None
    estado_aprobacion: str
    aprobado_por_usuario_id: UUID | None = None
    fecha_aprobacion: datetime | None = None
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)
