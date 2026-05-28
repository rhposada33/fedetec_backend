from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportePagoCrear(BaseModel):
    valor: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class ReportePagoLeer(BaseModel):
    id: UUID
    servicio_id: UUID
    tecnico_id: UUID
    empresa_cliente_id: UUID
    valor: Decimal | None = None
    estado: str
    fecha_generacion: datetime

    model_config = ConfigDict(from_attributes=True)
