from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UsuarioBase(BaseModel):
    correo: EmailStr
    nombre_completo: str = Field(min_length=1, max_length=255)


class UsuarioCrear(UsuarioBase):
    password: str = Field(min_length=8, max_length=128)


class UsuarioLeer(UsuarioBase):
    id: int
    es_activo: bool
    es_superusuario: bool
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)

