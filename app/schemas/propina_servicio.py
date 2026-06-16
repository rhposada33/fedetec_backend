from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PropinaServicioCrear(BaseModel):
    valor: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class PropinaServicioLeer(BaseModel):
    id: UUID
    servicio_id: UUID
    empresa_cliente_id: UUID
    tecnico_id: UUID
    valor: Decimal
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)
