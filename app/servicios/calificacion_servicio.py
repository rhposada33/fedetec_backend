from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.calificacion_servicio import CalificacionServicio
from app.modelos.empresa_cliente import EmpresaCliente
from app.repositorios.calificacion_servicio import (
    CalificacionDuplicadaError,
    CalificacionServicioRepositorio,
)
from app.repositorios.servicio import ServicioRepositorio
from app.schemas.calificacion_servicio import CalificacionServicioCrear

ESTADOS_CALIFICABLES = {"FINALIZADO", "VALIDADO", "PAGO_GENERADO"}


class CalificacionServicioServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.calificaciones = CalificacionServicioRepositorio(session)
        self.servicios = ServicioRepositorio(session)

    async def crear(
        self,
        servicio_id: UUID,
        empresa_cliente: EmpresaCliente,
        calificacion_in: CalificacionServicioCrear,
    ) -> CalificacionServicio | None:
        servicio_con_ubicacion = await self.servicios.obtener_por_id(servicio_id)
        if servicio_con_ubicacion is None:
            return None

        servicio = servicio_con_ubicacion.servicio
        if servicio.empresa_cliente_id != empresa_cliente.id:
            raise PermissionError("Solo la empresa propietaria puede calificar el servicio")
        if servicio.estado not in ESTADOS_CALIFICABLES:
            raise ValueError("Solo se pueden calificar servicios finalizados, validados o pagados")
        if servicio.tecnico_aceptado_id is None:
            raise ValueError("El servicio no tiene tecnico asignado")

        existente = await self.calificaciones.obtener_por_servicio(servicio_id)
        if existente is not None:
            raise CalificacionDuplicadaError("El servicio ya fue calificado")

        calificacion = CalificacionServicio(
            servicio_id=servicio.id,
            empresa_cliente_id=empresa_cliente.id,
            tecnico_id=servicio.tecnico_aceptado_id,
            puntuacion=calificacion_in.puntuacion,
            comentario=calificacion_in.comentario,
        )
        return await self.calificaciones.crear(calificacion)

    async def obtener(
        self, servicio_id: UUID, empresa_cliente: EmpresaCliente
    ) -> CalificacionServicio | None:
        servicio_con_ubicacion = await self.servicios.obtener_por_id(servicio_id)
        if servicio_con_ubicacion is None:
            return None

        servicio = servicio_con_ubicacion.servicio
        if servicio.empresa_cliente_id != empresa_cliente.id:
            raise PermissionError("Solo la empresa propietaria puede consultar la calificacion")

        return await self.calificaciones.obtener_por_servicio(servicio_id)
