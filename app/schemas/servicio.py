from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ServicioCrear(BaseModel):
    tipo_servicio: Literal[1, 2, 3]
    placa_vehiculo: str | None = Field(default=None, max_length=30)
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    direccion: str | None = None
    fecha_programada: datetime


class ServicioLeer(BaseModel):
    id: UUID
    empresa_cliente_id: UUID
    tipo_servicio: int
    placa_vehiculo: str | None = None
    latitud: float
    longitud: float
    direccion: str | None = None
    fecha_programada: datetime
    estado: str
    clave_idempotencia: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime
