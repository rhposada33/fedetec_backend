from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.reporte_pago import ReportePago
from app.repositorios.propina_servicio import PropinaServicioRepositorio
from app.repositorios.reporte_pago import ReportePagoDuplicadoError, ReportePagoRepositorio
from app.repositorios.servicio import ServicioRepositorio
from app.schemas.reporte_pago import ReportePagoCrear

ESTADOS_SERVICIO_REPORTE_PAGO = {"FINALIZADO", "VALIDADO"}


class ReportePagoServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.propinas = PropinaServicioRepositorio(session)
        self.reportes = ReportePagoRepositorio(session)
        self.servicios = ServicioRepositorio(session)

    async def crear(self, servicio_id: UUID, reporte_in: ReportePagoCrear) -> ReportePago | None:
        servicio = await self.servicios.obtener_por_id_para_actualizar(servicio_id)
        if servicio is None:
            return None
        if servicio.estado not in ESTADOS_SERVICIO_REPORTE_PAGO:
            raise ValueError("Solo servicios FINALIZADO o VALIDADO permiten reporte de pago")
        if servicio.tecnico_aceptado_id is None:
            raise ValueError("El servicio no tiene tecnico asignado")

        existente = await self.reportes.obtener_por_servicio_id(servicio_id)
        if existente is not None:
            raise ReportePagoDuplicadoError("Ya existe un reporte de pago para este servicio")

        valor_base = reporte_in.valor
        if valor_base is None:
            valor_base = getattr(servicio, "valor_servicio", 0)
        propina = await self.propinas.obtener_por_servicio(servicio_id)
        valor_propina = propina.valor if propina is not None else 0

        reporte = ReportePago(
            servicio_id=servicio.id,
            tecnico_id=servicio.tecnico_aceptado_id,
            empresa_cliente_id=servicio.empresa_cliente_id,
            valor_base=valor_base,
            valor_propina=valor_propina,
            valor=valor_base + valor_propina,
            estado="GENERADO",
        )
        await self.reportes.crear(reporte)
        servicio.estado = "PAGO_GENERADO"
        servicio.fecha_pago_generado = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(reporte)
        return reporte

    async def listar(self) -> list[ReportePago]:
        return await self.reportes.listar()

    async def obtener(self, reporte_id: UUID) -> ReportePago | None:
        return await self.reportes.obtener_por_id(reporte_id)
