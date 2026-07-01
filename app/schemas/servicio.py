from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ServicioCrear(BaseModel):
    empresa_cliente_id: UUID | None = None
    tipo_servicio: int = Field(gt=0)
    placa_vehiculo: str | None = Field(default=None, max_length=30)
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    direccion: str | None = None
    fecha_programada: datetime


class ServicioActualizar(BaseModel):
    empresa_cliente_id: UUID | None = None
    tipo_servicio: int | None = Field(default=None, gt=0)
    placa_vehiculo: str | None = Field(default=None, max_length=30)
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)
    direccion: str | None = None
    fecha_programada: datetime | None = None


class ServicioLeer(BaseModel):
    id: UUID
    empresa_cliente_id: UUID
    tipo_servicio: int
    tipo_servicio_nombre: str
    valor_servicio: Decimal
    placa_vehiculo: str | None = None
    latitud: float
    longitud: float
    direccion: str | None = None
    fecha_programada: datetime
    estado: str
    clave_idempotencia: str
    tecnico_aceptado_id: UUID | None = None
    fecha_aceptacion: datetime | None = None
    fecha_inicio: datetime | None = None
    fecha_finalizacion: datetime | None = None
    fecha_validacion: datetime | None = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class ServicioPublicadoLeer(ServicioLeer):
    notificaciones_creadas: int
    tecnicos_cercanos: int


class ResumenEntregaNotificaciones(BaseModel):
    servicio_id: UUID
    total: int
    recibidas: int
    enviadas_proveedor: int
    pendientes: int
    fallidas: int


class ServicioRechazar(BaseModel):
    motivo: str | None = None


class ServicioReprogramar(BaseModel):
    fecha_propuesta: datetime
    motivo: str | None = None


class ServicioReasignar(BaseModel):
    tecnico_id: UUID
    motivo: str | None = None


class ReprogramacionServicioLeer(BaseModel):
    id: UUID
    servicio_id: UUID
    tecnico_id: UUID
    fecha_propuesta: datetime
    motivo: str | None = None
    estado: str
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)


class ServicioRechazadoLeer(BaseModel):
    servicio_id: UUID
    tecnico_id: UUID
    rechazo_creado: bool
    estado: str


class HistorialServicioEventoLeer(BaseModel):
    fecha: datetime
    tipo_evento: str
    titulo: str
    descripcion: str | None = None
    entidad: str | None = None
    entidad_id: UUID | None = None
    datos: dict[str, Any] = Field(default_factory=dict)
