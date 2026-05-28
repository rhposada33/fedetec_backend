from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmpresaClienteBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    identificacion_tributaria: str | None = Field(default=None, max_length=80)
    correo_contacto: EmailStr | None = None
    telefono_contacto: str | None = Field(default=None, max_length=50)
    esta_activa: bool = True


class EmpresaClienteCrear(EmpresaClienteBase):
    pass


class EmpresaClienteActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    identificacion_tributaria: str | None = Field(default=None, max_length=80)
    correo_contacto: EmailStr | None = None
    telefono_contacto: str | None = Field(default=None, max_length=50)
    esta_activa: bool | None = None


class EmpresaClienteLeer(EmpresaClienteBase):
    id: UUID
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)


class EmpresaClienteCreada(EmpresaClienteLeer):
    api_key: str
