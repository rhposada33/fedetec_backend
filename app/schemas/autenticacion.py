from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TecnicoRegistrar(BaseModel):
    correo: EmailStr
    contrasena: str = Field(min_length=8, max_length=128)
    nombre_completo: str = Field(min_length=1, max_length=150)
    telefono: str | None = Field(default=None, max_length=50)
    numero_documento: str | None = Field(default=None, max_length=50)
    ciudad: str | None = Field(default=None, max_length=100)
    municipio: str | None = Field(default=None, max_length=100)
    direccion: str | None = None
    eps: str | None = Field(default=None, max_length=100)
    arl: str | None = Field(default=None, max_length=100)
    tiene_vehiculo: bool = False
    placa_vehiculo: str | None = Field(default=None, max_length=30)


class UsuarioAutenticadoLeer(BaseModel):
    id: UUID
    tecnico_id: UUID | None = None
    correo: EmailStr
    nombre_completo: str
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
    roles: list[str] = Field(default_factory=list)
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)
