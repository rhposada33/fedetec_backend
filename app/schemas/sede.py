from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SedeBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=180)
    direccion: str | None = None
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)


class SedeCrear(SedeBase):
    pass


class SedeLeer(BaseModel):
    id: int
    nombre: str
    direccion: str | None
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)

