from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.api.deps import (
    AdminDep,
    EmpresaClienteActualDep,
    SesionDep,
    TecnicoActualDep,
    UsuarioActualDep,
    usuario_es_admin,
    usuario_es_empresa_cliente,
)
from app.modelos.empresa_cliente import EmpresaCliente
from app.repositorios.calificacion_servicio import CalificacionDuplicadaError
from app.repositorios.empresa_cliente import EmpresaClienteRepositorio
from app.repositorios.propina_servicio import PropinaDuplicadaError
from app.repositorios.reporte_pago import ReportePagoDuplicadoError
from app.schemas.calificacion_servicio import CalificacionServicioCrear, CalificacionServicioLeer
from app.schemas.evidencia_servicio import (
    EvidenciaServicioCrear,
    EvidenciaServicioLeer,
    EvidenciaUploadUrlLeer,
    EvidenciaUploadUrlSolicitar,
)
from app.schemas.propina_servicio import PropinaServicioCrear, PropinaServicioLeer
from app.schemas.reporte_pago import ReportePagoCrear, ReportePagoLeer
from app.schemas.servicio import (
    HistorialServicioEventoLeer,
    ReprogramacionServicioLeer,
    ServicioActualizar,
    ServicioCrear,
    ServicioLeer,
    ServicioPublicadoLeer,
    ServicioReasignar,
    ServicioRechazadoLeer,
    ServicioRechazar,
    ServicioReprogramar,
)
from app.servicios.calificacion_servicio import CalificacionServicioServicio
from app.servicios.evidencia_servicio import EvidenciaServicioServicio
from app.servicios.propina_servicio import PropinaServicioServicio
from app.servicios.reporte_pago import ReportePagoServicio
from app.servicios.servicio import ServicioServicio

router = APIRouter()


@router.post("", response_model=ServicioLeer, status_code=status.HTTP_201_CREATED)
async def crear_servicio(
    servicio_in: ServicioCrear,
    session: SesionDep,
    usuario_actual: UsuarioActualDep,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", max_length=150)
    ] = None,
) -> ServicioLeer:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header Idempotency-Key requerido",
        )

    empresa_cliente = await _resolver_empresa_para_crear_servicio(
        session, usuario_actual, servicio_in
    )
    try:
        return await ServicioServicio(session).crear(
            servicio_in, empresa_cliente, idempotency_key.strip()
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[ServicioLeer])
async def listar_servicios(
    session: SesionDep, usuario_actual: UsuarioActualDep
) -> list[ServicioLeer]:
    servicio = ServicioServicio(session)
    if usuario_es_admin(usuario_actual):
        return await servicio.listar_admin()
    if usuario_es_empresa_cliente(usuario_actual) and usuario_actual.empresa_cliente is not None:
        return await servicio.listar(usuario_actual.empresa_cliente)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado")


@router.get("/{servicio_id}", response_model=ServicioLeer)
async def obtener_servicio(
    servicio_id: UUID, session: SesionDep, usuario_actual: UsuarioActualDep
) -> ServicioLeer:
    servicio_servicio = ServicioServicio(session)
    if usuario_es_admin(usuario_actual):
        servicio = await servicio_servicio.obtener_admin(servicio_id)
    elif usuario_es_empresa_cliente(usuario_actual) and usuario_actual.empresa_cliente is not None:
        servicio = await servicio_servicio.obtener(servicio_id, usuario_actual.empresa_cliente)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado")
    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.get("/{servicio_id}/historial", response_model=list[HistorialServicioEventoLeer])
async def obtener_historial_servicio(
    servicio_id: UUID, session: SesionDep, usuario_actual: UsuarioActualDep
) -> list[HistorialServicioEventoLeer]:
    servicio_servicio = ServicioServicio(session)
    if usuario_es_admin(usuario_actual):
        historial = await servicio_servicio.obtener_historial_admin(servicio_id)
    elif usuario_es_empresa_cliente(usuario_actual) and usuario_actual.empresa_cliente is not None:
        historial = await servicio_servicio.obtener_historial_empresa(
            servicio_id, usuario_actual.empresa_cliente
        )
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado")

    if historial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return historial


@router.patch("/{servicio_id}", response_model=ServicioLeer)
async def actualizar_servicio(
    servicio_id: UUID,
    servicio_in: ServicioActualizar,
    session: SesionDep,
    _admin: AdminDep,
) -> ServicioLeer:
    empresa_cliente = None
    if servicio_in.empresa_cliente_id is not None:
        empresa_cliente = await EmpresaClienteRepositorio(session).obtener_por_id(
            servicio_in.empresa_cliente_id
        )
        if empresa_cliente is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa cliente no encontrada",
            )
        if not empresa_cliente.esta_activa:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La empresa cliente no esta activa",
            )

    try:
        servicio = await ServicioServicio(session).actualizar(
            servicio_id, servicio_in, empresa_cliente
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.post(
    "/{servicio_id}/calificaciones",
    response_model=CalificacionServicioLeer,
    status_code=status.HTTP_201_CREATED,
)
async def crear_calificacion_servicio(
    servicio_id: UUID,
    calificacion_in: CalificacionServicioCrear,
    session: SesionDep,
    empresa_cliente: EmpresaClienteActualDep,
) -> CalificacionServicioLeer:
    try:
        calificacion = await CalificacionServicioServicio(session).crear(
            servicio_id, empresa_cliente, calificacion_in
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except CalificacionDuplicadaError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if calificacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return calificacion


@router.get("/{servicio_id}/calificaciones", response_model=CalificacionServicioLeer)
async def obtener_calificacion_servicio(
    servicio_id: UUID,
    session: SesionDep,
    empresa_cliente: EmpresaClienteActualDep,
) -> CalificacionServicioLeer:
    try:
        calificacion = await CalificacionServicioServicio(session).obtener(
            servicio_id, empresa_cliente
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if calificacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calificacion no encontrada",
        )
    return calificacion


@router.post(
    "/{servicio_id}/propina",
    response_model=PropinaServicioLeer,
    status_code=status.HTTP_201_CREATED,
)
async def crear_propina_servicio(
    servicio_id: UUID,
    propina_in: PropinaServicioCrear,
    session: SesionDep,
    empresa_cliente: EmpresaClienteActualDep,
) -> PropinaServicioLeer:
    try:
        propina = await PropinaServicioServicio(session).crear(
            servicio_id, empresa_cliente, propina_in
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PropinaDuplicadaError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if propina is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return propina


@router.get("/{servicio_id}/propina", response_model=PropinaServicioLeer)
async def obtener_propina_servicio(
    servicio_id: UUID,
    session: SesionDep,
    empresa_cliente: EmpresaClienteActualDep,
) -> PropinaServicioLeer:
    try:
        propina = await PropinaServicioServicio(session).obtener(servicio_id, empresa_cliente)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if propina is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Propina no encontrada",
        )
    return propina


async def _resolver_empresa_para_crear_servicio(
    session: SesionDep, usuario_actual: UsuarioActualDep, servicio_in: ServicioCrear
) -> EmpresaCliente:
    if usuario_es_admin(usuario_actual):
        if servicio_in.empresa_cliente_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="empresa_cliente_id es requerido para administradores",
            )
        empresa = await EmpresaClienteRepositorio(session).obtener_por_id(
            servicio_in.empresa_cliente_id
        )
        if empresa is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa cliente no encontrada",
            )
        if not empresa.esta_activa:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La empresa cliente no esta activa",
            )
        return empresa

    if usuario_es_empresa_cliente(usuario_actual) and usuario_actual.empresa_cliente is not None:
        if not usuario_actual.empresa_cliente.esta_activa:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La empresa cliente no esta activa",
            )
        return usuario_actual.empresa_cliente

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso no autorizado")


@router.post("/{servicio_id}/publicar", response_model=ServicioPublicadoLeer)
async def publicar_servicio(
    servicio_id: UUID,
    session: SesionDep,
    _admin: AdminDep,
    radio_metros: Annotated[int, Query(gt=0, le=100_000)] = 10_000,
) -> ServicioPublicadoLeer:
    try:
        servicio = await ServicioServicio(session).publicar(servicio_id, radio_metros)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.post("/{servicio_id}/aceptar", response_model=ServicioLeer)
async def aceptar_servicio(
    servicio_id: UUID,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> ServicioLeer:
    try:
        servicio = await ServicioServicio(session).aceptar(servicio_id, tecnico_actual)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.post("/{servicio_id}/rechazar", response_model=ServicioRechazadoLeer)
async def rechazar_servicio(
    servicio_id: UUID,
    rechazo_in: ServicioRechazar,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> ServicioRechazadoLeer:
    rechazo = await ServicioServicio(session).rechazar(servicio_id, tecnico_actual, rechazo_in)
    if rechazo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return rechazo


@router.post("/{servicio_id}/reprogramar", response_model=ReprogramacionServicioLeer)
async def reprogramar_servicio(
    servicio_id: UUID,
    reprogramacion_in: ServicioReprogramar,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> ReprogramacionServicioLeer:
    try:
        reprogramacion = await ServicioServicio(session).reprogramar(
            servicio_id, tecnico_actual, reprogramacion_in
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if reprogramacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return reprogramacion


@router.post("/{servicio_id}/iniciar", response_model=ServicioLeer)
async def iniciar_servicio(
    servicio_id: UUID,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> ServicioLeer:
    try:
        servicio = await ServicioServicio(session).iniciar(servicio_id, tecnico_actual)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.post("/{servicio_id}/finalizar", response_model=ServicioLeer)
async def finalizar_servicio(
    servicio_id: UUID,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> ServicioLeer:
    try:
        servicio = await ServicioServicio(session).finalizar(servicio_id, tecnico_actual)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.post("/{servicio_id}/validar", response_model=ServicioLeer)
async def validar_servicio(
    servicio_id: UUID,
    session: SesionDep,
    _admin: AdminDep,
) -> ServicioLeer:
    try:
        servicio = await ServicioServicio(session).validar(servicio_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.post("/{servicio_id}/reasignar", response_model=ServicioLeer)
async def reasignar_servicio(
    servicio_id: UUID,
    reasignacion_in: ServicioReasignar,
    session: SesionDep,
    _admin: AdminDep,
) -> ServicioLeer:
    try:
        servicio = await ServicioServicio(session).reasignar(servicio_id, reasignacion_in)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return servicio


@router.post("/{servicio_id}/evidencias", response_model=EvidenciaServicioLeer)
async def crear_evidencia_servicio(
    servicio_id: UUID,
    evidencia_in: EvidenciaServicioCrear,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> EvidenciaServicioLeer:
    try:
        evidencia = await EvidenciaServicioServicio(session).crear(
            servicio_id, tecnico_actual, evidencia_in
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if evidencia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return evidencia


@router.post(
    "/{servicio_id}/evidencias/upload-url",
    response_model=EvidenciaUploadUrlLeer,
)
async def crear_upload_url_evidencia_servicio(
    servicio_id: UUID,
    upload_in: EvidenciaUploadUrlSolicitar,
    session: SesionDep,
    tecnico_actual: TecnicoActualDep,
) -> EvidenciaUploadUrlLeer:
    try:
        upload = await EvidenciaServicioServicio(session).crear_upload_url(
            servicio_id, tecnico_actual, upload_in
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return upload


@router.get("/{servicio_id}/evidencias", response_model=list[EvidenciaServicioLeer])
async def listar_evidencias_servicio(
    servicio_id: UUID,
    session: SesionDep,
    usuario_actual: UsuarioActualDep,
) -> list[EvidenciaServicioLeer]:
    try:
        evidencias = await EvidenciaServicioServicio(session).listar_por_servicio(
            servicio_id, usuario_actual
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if evidencias is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return evidencias


@router.post("/{servicio_id}/reporte-pago", response_model=ReportePagoLeer)
async def crear_reporte_pago_servicio(
    servicio_id: UUID,
    reporte_in: ReportePagoCrear,
    session: SesionDep,
    _admin: AdminDep,
) -> ReportePagoLeer:
    try:
        reporte = await ReportePagoServicio(session).crear(servicio_id, reporte_in)
    except ReportePagoDuplicadoError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if reporte is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )
    return reporte
