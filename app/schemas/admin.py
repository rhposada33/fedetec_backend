from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DashboardEstadoMetrica(BaseModel):
    estado: str
    total: int


class DashboardLeer(BaseModel):
    total_servicios: int
    servicios_por_estado: list[DashboardEstadoMetrica]


class ConfiguracionAprobacionEvidenciasLeer(BaseModel):
    modo: Literal["AUTO", "MANUAL"] = "MANUAL"
    roles_permitidos: list[str] = Field(default_factory=lambda: ["ADMIN"])


class ConfiguracionActualizar(BaseModel):
    aprobacion_evidencias: ConfiguracionAprobacionEvidenciasLeer


class ConfiguracionLeer(BaseModel):
    aprobacion_evidencias: ConfiguracionAprobacionEvidenciasLeer
    fecha_actualizacion: datetime | None = None
