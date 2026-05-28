from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
