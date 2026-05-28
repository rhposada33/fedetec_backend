from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UsuarioBase(BaseModel):
    correo: EmailStr
    nombre_completo: str = Field(min_length=1, max_length=150)


class UsuarioCrear(UsuarioBase):
    password: str = Field(min_length=8, max_length=128)


class UsuarioLeer(UsuarioBase):
    id: UUID
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
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)
