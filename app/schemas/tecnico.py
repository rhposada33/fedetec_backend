from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.servicio import ServicioLeer


class UbicacionTecnicoActualizar(BaseModel):
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)


class DisponibilidadTecnicoActualizar(BaseModel):
    esta_disponible: bool


class TecnicoLeer(BaseModel):
    id: UUID
    usuario_id: UUID
    nombre_completo: str
    correo: str
    telefono: str | None = None
    esta_disponible: bool
    latitud: float | None = None
    longitud: float | None = None
    fecha_ultima_ubicacion: datetime | None = None
    fecha_creacion: datetime


class TecnicoCercanoLeer(TecnicoLeer):
    distancia_metros: float


class MetricasRendimientoTecnicoLeer(BaseModel):
    tecnico_id: UUID
    calificacion_promedio: float | None = None
    servicios_completados: int
    servicios_aceptados: int
    servicios_rechazados: int


class NotificacionServicioTecnicoLeer(BaseModel):
    id: UUID
    servicio_id: UUID
    tecnico_id: UUID
    estado: str
    fecha_envio: datetime
    fecha_lectura: datetime | None = None
    servicio: ServicioLeer
