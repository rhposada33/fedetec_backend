from datetime import datetime
from uuid import UUID

from pydantic import AnyUrl, BaseModel, ConfigDict, Field


class EvidenciaServicioCrear(BaseModel):
    url_archivo: AnyUrl
    storage_key: str | None = Field(default=None, max_length=500)
    tipo_archivo: str | None = Field(default=None, max_length=50)
    descripcion: str | None = None


class EvidenciaUploadUrlSolicitar(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)


class EvidenciaUploadUrlLeer(BaseModel):
    upload_url: str
    public_url: str
    storage_key: str


class EvidenciaServicioLeer(BaseModel):
    id: UUID
    servicio_id: UUID
    subido_por_usuario_id: UUID
    url_archivo: str
    storage_key: str | None = None
    tipo_archivo: str | None = None
    descripcion: str | None = None
    estado_aprobacion: str
    aprobado_por_usuario_id: UUID | None = None
    fecha_aprobacion: datetime | None = None
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)
