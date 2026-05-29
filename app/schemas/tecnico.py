from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.servicio import ServicioLeer


class UbicacionTecnicoActualizar(BaseModel):
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)


class DisponibilidadTecnicoActualizar(BaseModel):
    esta_disponible: bool


class TecnicoActualizar(BaseModel):
    nombre_completo: str | None = Field(default=None, min_length=1, max_length=150)
    correo: str | None = Field(default=None, max_length=150)
    telefono: str | None = Field(default=None, max_length=50)
    numero_documento: str | None = Field(default=None, max_length=50)
    ciudad: str | None = Field(default=None, max_length=100)
    municipio: str | None = Field(default=None, max_length=100)
    direccion: str | None = None
    eps: str | None = Field(default=None, max_length=100)
    arl: str | None = Field(default=None, max_length=100)
    tiene_vehiculo: bool | None = None
    placa_vehiculo: str | None = Field(default=None, max_length=30)
    esta_activo: bool | None = None
    esta_disponible: bool | None = None
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)


class TecnicoLeer(BaseModel):
    id: UUID
    usuario_id: UUID
    nombre_completo: str
    correo: str
    telefono: str | None = None
    numero_documento: str | None = None
    ciudad: str | None = None
    municipio: str | None = None
    direccion: str | None = None
    eps: str | None = None
    arl: str | None = None
    tiene_vehiculo: bool
    placa_vehiculo: str | None = None
    esta_activo: bool
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
