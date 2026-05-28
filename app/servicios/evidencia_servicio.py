from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.evidencia_servicio import EvidenciaServicio
from app.modelos.tecnico import Tecnico
from app.modelos.usuario import Usuario
from app.repositorios.configuracion_app import ConfiguracionAppRepositorio
from app.repositorios.evidencia_servicio import EvidenciaServicioRepositorio
from app.repositorios.servicio import ServicioRepositorio
from app.schemas.evidencia_servicio import EvidenciaServicioCrear

CONFIG_APROBACION_EVIDENCIAS = "aprobacion_evidencias"
MODO_APROBACION_AUTO = "AUTO"
MODO_APROBACION_MANUAL = "MANUAL"


class EvidenciaServicioServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.evidencias = EvidenciaServicioRepositorio(session)
        self.servicios = ServicioRepositorio(session)
        self.configuracion = ConfiguracionAppRepositorio(session)

    async def crear(
        self, servicio_id: UUID, tecnico: Tecnico, evidencia_in: EvidenciaServicioCrear
    ) -> EvidenciaServicio | None:
        servicio = await self.servicios.obtener_por_id(servicio_id)
        if servicio is None:
            return None
        if servicio.servicio.tecnico_aceptado_id != tecnico.id:
            raise PermissionError("Solo el tecnico asignado puede subir evidencias")

        aprobacion_auto = await self._aprobacion_automatica_activa()
        evidencia = EvidenciaServicio(
            servicio_id=servicio_id,
            subido_por_usuario_id=tecnico.usuario_id,
            url_archivo=str(evidencia_in.url_archivo),
            tipo_archivo=evidencia_in.tipo_archivo,
            descripcion=evidencia_in.descripcion,
            estado_aprobacion="APROBADA" if aprobacion_auto else "PENDIENTE",
            aprobado_por_usuario_id=tecnico.usuario_id if aprobacion_auto else None,
            fecha_aprobacion=datetime.now(UTC) if aprobacion_auto else None,
        )
        return await self.evidencias.crear(evidencia)

    async def listar_por_servicio(
        self, servicio_id: UUID, usuario_actual: Usuario
    ) -> list[EvidenciaServicio] | None:
        servicio = await self.servicios.obtener_por_id(servicio_id)
        if servicio is None:
            return None
        if not self._es_admin(usuario_actual):
            tecnico = usuario_actual.tecnico
            if tecnico is None or servicio.servicio.tecnico_aceptado_id != tecnico.id:
                raise PermissionError("No tiene permisos para ver las evidencias")
        return await self.evidencias.listar_por_servicio(servicio_id)

    async def aprobar(self, evidencia_id: UUID, admin: Usuario) -> EvidenciaServicio | None:
        evidencia = await self.evidencias.obtener_por_id(evidencia_id)
        if evidencia is None:
            return None
        evidencia.estado_aprobacion = "APROBADA"
        evidencia.aprobado_por_usuario_id = admin.id
        evidencia.fecha_aprobacion = datetime.now(UTC)
        return await self.evidencias.guardar(evidencia)

    async def rechazar(self, evidencia_id: UUID, admin: Usuario) -> EvidenciaServicio | None:
        evidencia = await self.evidencias.obtener_por_id(evidencia_id)
        if evidencia is None:
            return None
        evidencia.estado_aprobacion = "RECHAZADA"
        evidencia.aprobado_por_usuario_id = admin.id
        evidencia.fecha_aprobacion = datetime.now(UTC)
        return await self.evidencias.guardar(evidencia)

    async def _aprobacion_automatica_activa(self) -> bool:
        configuracion = await self.configuracion.obtener_valor(CONFIG_APROBACION_EVIDENCIAS)
        modo = (configuracion or {}).get("modo", MODO_APROBACION_MANUAL)
        return modo == MODO_APROBACION_AUTO

    @staticmethod
    def _es_admin(usuario: Usuario) -> bool:
        return any(usuario_rol.rol.nombre == "ADMIN" for usuario_rol in usuario.roles)
