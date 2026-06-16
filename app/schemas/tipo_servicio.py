from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TipoServicioCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    valor: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    esta_activo: bool = True


class TipoServicioActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    valor: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    esta_activo: bool | None = None


class TipoServicioLeer(BaseModel):
    id: int
    nombre: str
    valor: Decimal
    esta_activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    model_config = ConfigDict(from_attributes=True)
