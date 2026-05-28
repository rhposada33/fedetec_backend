from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminDep, SesionDep
from app.schemas.reporte_pago import ReportePagoLeer
from app.servicios.reporte_pago import ReportePagoServicio

router = APIRouter()


@router.get("", response_model=list[ReportePagoLeer])
async def listar_reportes_pago(session: SesionDep, _admin: AdminDep) -> list[ReportePagoLeer]:
    return await ReportePagoServicio(session).listar()


@router.get("/{reporte_id}", response_model=ReportePagoLeer)
async def obtener_reporte_pago(
    reporte_id: UUID, session: SesionDep, _admin: AdminDep
) -> ReportePagoLeer:
    reporte = await ReportePagoServicio(session).obtener(reporte_id)
    if reporte is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reporte de pago no encontrado",
        )
    return reporte
