from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import SesionDep, UsuarioActualDep, usuario_es_admin, usuario_es_empresa_cliente
from app.schemas.reporte_pago import ReportePagoLeer
from app.servicios.reporte_pago import ReportePagoServicio

router = APIRouter()


@router.get("", response_model=list[ReportePagoLeer])
async def listar_reportes_pago(
    session: SesionDep, usuario: UsuarioActualDep
) -> list[ReportePagoLeer]:
    servicio = ReportePagoServicio(session)
    if usuario_es_admin(usuario):
        return await servicio.listar()
    if usuario_es_empresa_cliente(usuario) and usuario.empresa_cliente is not None:
        return await servicio.listar_por_empresa(usuario.empresa_cliente.id)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado")


@router.get("/{reporte_id}", response_model=ReportePagoLeer)
async def obtener_reporte_pago(
    reporte_id: UUID, session: SesionDep, usuario: UsuarioActualDep
) -> ReportePagoLeer:
    reporte = await ReportePagoServicio(session).obtener(reporte_id)
    if reporte is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reporte de pago no encontrado",
        )
    if not usuario_es_admin(usuario):
        empresa = usuario.empresa_cliente
        if empresa is None or reporte.empresa_cliente_id != empresa.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado"
            )
    return reporte
