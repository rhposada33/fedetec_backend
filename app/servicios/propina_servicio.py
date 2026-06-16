from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.empresa_cliente import EmpresaCliente
from app.modelos.propina_servicio import PropinaServicio
from app.repositorios.propina_servicio import PropinaDuplicadaError, PropinaServicioRepositorio
from app.repositorios.reporte_pago import ReportePagoRepositorio
from app.repositorios.servicio import ServicioRepositorio
from app.schemas.propina_servicio import PropinaServicioCrear

ESTADOS_SERVICIO_PROPINA = {"FINALIZADO", "VALIDADO", "PAGO_GENERADO"}
ESTADOS_REPORTE_BLOQUEAN_PROPINA = {"PAGADO", "ANULADO"}
ESTADOS_REPORTE_RECALCULABLES = {"PENDIENTE", "GENERADO"}


class PropinaServicioServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.propinas = PropinaServicioRepositorio(session)
        self.reportes = ReportePagoRepositorio(session)
        self.servicios = ServicioRepositorio(session)

    async def crear(
        self,
        servicio_id: UUID,
        empresa_cliente: EmpresaCliente,
        propina_in: PropinaServicioCrear,
    ) -> PropinaServicio | None:
        servicio_con_ubicacion = await self.servicios.obtener_por_id(servicio_id)
        if servicio_con_ubicacion is None:
            return None

        servicio = servicio_con_ubicacion.servicio
        if servicio.empresa_cliente_id != empresa_cliente.id:
            raise PermissionError("Solo la empresa propietaria puede dar propina")
        if servicio.estado not in ESTADOS_SERVICIO_PROPINA:
            raise ValueError("Solo servicios finalizados, validados o pagados permiten propina")
        if servicio.tecnico_aceptado_id is None:
            raise ValueError("El servicio no tiene tecnico asignado")

        existente = await self.propinas.obtener_por_servicio(servicio_id)
        if existente is not None:
            raise PropinaDuplicadaError("El servicio ya tiene propina registrada")

        reporte = await self.reportes.obtener_por_servicio_id(servicio_id)
        if reporte is not None and reporte.estado in ESTADOS_REPORTE_BLOQUEAN_PROPINA:
            raise ValueError("No se puede dar propina a un reporte pagado o anulado")

        propina = PropinaServicio(
            servicio_id=servicio.id,
            empresa_cliente_id=empresa_cliente.id,
            tecnico_id=servicio.tecnico_aceptado_id,
            valor=propina_in.valor,
        )
        await self.propinas.crear(propina)

        if reporte is not None and reporte.estado in ESTADOS_REPORTE_RECALCULABLES:
            reporte.valor_propina = propina.valor
            reporte.valor = (reporte.valor_base or 0) + propina.valor

        await self.session.commit()
        await self.session.refresh(propina)
        return propina

    async def obtener(
        self, servicio_id: UUID, empresa_cliente: EmpresaCliente
    ) -> PropinaServicio | None:
        servicio_con_ubicacion = await self.servicios.obtener_por_id(servicio_id)
        if servicio_con_ubicacion is None:
            return None

        servicio = servicio_con_ubicacion.servicio
        if servicio.empresa_cliente_id != empresa_cliente.id:
            raise PermissionError("Solo la empresa propietaria puede consultar la propina")

        return await self.propinas.obtener_por_servicio(servicio_id)
