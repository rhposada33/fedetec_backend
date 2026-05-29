from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminDep, SesionDep
from app.schemas.admin import ConfiguracionActualizar, ConfiguracionLeer, DashboardLeer
from app.schemas.empresa_cliente import EmpresaClienteLeer
from app.schemas.evidencia_servicio import EvidenciaServicioLeer
from app.schemas.servicio import ServicioLeer
from app.schemas.tecnico import MetricasRendimientoTecnicoLeer, TecnicoLeer
from app.servicios.admin import AdminServicio

router = APIRouter()


@router.get("/dashboard", response_model=DashboardLeer)
async def obtener_dashboard(
    session: SesionDep,
    _admin: AdminDep,
    estado: str | None = None,
    empresa_cliente_id: UUID | None = None,
    tecnico_id: UUID | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
) -> DashboardLeer:
    return await AdminServicio(session).dashboard(
        estado, empresa_cliente_id, tecnico_id, fecha_desde, fecha_hasta
    )


@router.get("/servicios", response_model=list[ServicioLeer])
async def listar_servicios_admin(
    session: SesionDep,
    _admin: AdminDep,
    estado: str | None = None,
    empresa_cliente_id: UUID | None = None,
    tecnico_id: UUID | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
) -> list[ServicioLeer]:
    return await AdminServicio(session).listar_servicios(
        estado, empresa_cliente_id, tecnico_id, fecha_desde, fecha_hasta
    )


@router.get("/tecnicos", response_model=list[TecnicoLeer])
async def listar_tecnicos_admin(
    session: SesionDep,
    _admin: AdminDep,
    esta_disponible: bool | None = None,
) -> list[TecnicoLeer]:
    return await AdminServicio(session).listar_tecnicos(esta_disponible)


@router.get("/tecnicos/{tecnico_id}/metricas", response_model=MetricasRendimientoTecnicoLeer)
async def obtener_metricas_tecnico_admin(
    tecnico_id: UUID,
    session: SesionDep,
    _admin: AdminDep,
) -> MetricasRendimientoTecnicoLeer:
    metricas = await AdminServicio(session).obtener_metricas_tecnico(tecnico_id)
    if metricas is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tecnico no encontrado",
        )
    return metricas


@router.get("/empresas-cliente", response_model=list[EmpresaClienteLeer])
async def listar_empresas_cliente_admin(
    session: SesionDep,
    _admin: AdminDep,
    esta_activa: bool | None = None,
) -> list[EmpresaClienteLeer]:
    return await AdminServicio(session).listar_empresas_cliente(esta_activa)


@router.get("/evidencias/pendientes", response_model=list[EvidenciaServicioLeer])
async def listar_evidencias_pendientes_admin(
    session: SesionDep, _admin: AdminDep
) -> list[EvidenciaServicioLeer]:
    return await AdminServicio(session).listar_evidencias_pendientes()


@router.patch("/configuracion", response_model=ConfiguracionLeer)
async def actualizar_configuracion_admin(
    configuracion_in: ConfiguracionActualizar,
    session: SesionDep,
    _admin: AdminDep,
) -> ConfiguracionLeer:
    return await AdminServicio(session).actualizar_configuracion(configuracion_in)
