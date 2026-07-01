import re
from datetime import UTC, datetime
from pathlib import PurePath
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import ProveedorStorage, obtener_proveedor_storage
from app.modelos.evidencia_servicio import EvidenciaServicio
from app.modelos.tecnico import Tecnico
from app.modelos.usuario import Usuario
from app.repositorios.configuracion_app import ConfiguracionAppRepositorio
from app.repositorios.evidencia_servicio import EvidenciaServicioRepositorio
from app.repositorios.servicio import ServicioRepositorio
from app.schemas.evidencia_servicio import (
    EvidenciaServicioCrear,
    EvidenciaUploadUrlLeer,
    EvidenciaUploadUrlSolicitar,
)

CONFIG_APROBACION_EVIDENCIAS = "aprobacion_evidencias"
MODO_APROBACION_AUTO = "AUTO"
MODO_APROBACION_MANUAL = "MANUAL"
CONTENT_TYPES_EVIDENCIA_PERMITIDOS = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "video/mp4",
    "application/pdf",
}


class EvidenciaServicioServicio:
    def __init__(self, session: AsyncSession, storage: ProveedorStorage | None = None) -> None:
        self.evidencias = EvidenciaServicioRepositorio(session)
        self.servicios = ServicioRepositorio(session)
        self.configuracion = ConfiguracionAppRepositorio(session)
        self.storage = storage or obtener_proveedor_storage()

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
            storage_key=evidencia_in.storage_key,
            tipo_archivo=evidencia_in.tipo_archivo,
            descripcion=evidencia_in.descripcion,
            estado_aprobacion="APROBADA" if aprobacion_auto else "PENDIENTE",
            aprobado_por_usuario_id=tecnico.usuario_id if aprobacion_auto else None,
            fecha_aprobacion=datetime.now(UTC) if aprobacion_auto else None,
        )
        return await self.evidencias.crear(evidencia)

    async def crear_upload_url(
        self,
        servicio_id: UUID,
        tecnico: Tecnico,
        upload_in: EvidenciaUploadUrlSolicitar,
    ) -> EvidenciaUploadUrlLeer | None:
        servicio = await self.servicios.obtener_por_id(servicio_id)
        if servicio is None:
            return None
        if servicio.servicio.tecnico_aceptado_id != tecnico.id:
            raise PermissionError(
                "Solo el tecnico asignado o aceptado puede solicitar carga de evidencias"
            )

        content_type = upload_in.content_type.strip().lower()
        if content_type not in CONTENT_TYPES_EVIDENCIA_PERMITIDOS:
            raise ValueError("Tipo de archivo no permitido")

        storage_key = self._generar_storage_key(servicio_id, upload_in.filename)
        upload = await self.storage.crear_upload_url(storage_key, content_type)
        return EvidenciaUploadUrlLeer(
            upload_url=upload.upload_url,
            public_url=upload.public_url,
            storage_key=upload.storage_key,
        )

    async def listar_por_servicio(
        self, servicio_id: UUID, usuario_actual: Usuario
    ) -> list[EvidenciaServicio] | None:
        servicio = await self.servicios.obtener_por_id(servicio_id)
        if servicio is None:
            return None
        if not self._es_admin(usuario_actual):
            empresa = usuario_actual.empresa_cliente
            if empresa is not None and servicio.servicio.empresa_cliente_id == empresa.id:
                return await self.evidencias.listar_por_servicio(servicio_id)
            tecnico = usuario_actual.tecnico
            if tecnico is None or servicio.servicio.tecnico_aceptado_id != tecnico.id:
                raise PermissionError("No tiene permisos para ver las evidencias")
        return await self.evidencias.listar_por_servicio(servicio_id)

    async def listar_por_empresa(
        self, empresa_cliente_id: UUID, estado: str | None = None
    ) -> list[EvidenciaServicio]:
        return await self.evidencias.listar_por_empresa(empresa_cliente_id, estado)

    async def aprobar(self, evidencia_id: UUID, usuario: Usuario) -> EvidenciaServicio | None:
        evidencia = await self.evidencias.obtener_por_id(evidencia_id)
        if evidencia is None:
            return None
        await self._autorizar_revision(evidencia, usuario)
        evidencia.estado_aprobacion = "APROBADA"
        evidencia.aprobado_por_usuario_id = usuario.id
        evidencia.fecha_aprobacion = datetime.now(UTC)
        return await self.evidencias.guardar(evidencia)

    async def rechazar(self, evidencia_id: UUID, usuario: Usuario) -> EvidenciaServicio | None:
        evidencia = await self.evidencias.obtener_por_id(evidencia_id)
        if evidencia is None:
            return None
        await self._autorizar_revision(evidencia, usuario)
        evidencia.estado_aprobacion = "RECHAZADA"
        evidencia.aprobado_por_usuario_id = usuario.id
        evidencia.fecha_aprobacion = datetime.now(UTC)
        return await self.evidencias.guardar(evidencia)

    async def _autorizar_revision(self, evidencia: EvidenciaServicio, usuario: Usuario) -> None:
        # Compatibilidad con llamadas internas que ya recibieron un administrador validado.
        if not hasattr(usuario, "roles") and not hasattr(usuario, "empresa_cliente"):
            return
        if self._es_admin(usuario):
            return
        empresa = usuario.empresa_cliente
        servicio = await self.servicios.obtener_por_id(evidencia.servicio_id)
        if (
            empresa is None
            or servicio is None
            or servicio.servicio.empresa_cliente_id != empresa.id
        ):
            raise PermissionError("Solo la empresa propietaria puede revisar esta evidencia")

    async def _aprobacion_automatica_activa(self) -> bool:
        configuracion = await self.configuracion.obtener_valor(CONFIG_APROBACION_EVIDENCIAS)
        modo = (configuracion or {}).get("modo", MODO_APROBACION_MANUAL)
        return modo == MODO_APROBACION_AUTO

    @staticmethod
    def _es_admin(usuario: Usuario) -> bool:
        return any(usuario_rol.rol.nombre == "ADMIN" for usuario_rol in usuario.roles)

    @staticmethod
    def _generar_storage_key(servicio_id: UUID, filename: str) -> str:
        nombre = PurePath(filename).name.strip()
        nombre = re.sub(r"[^A-Za-z0-9._-]+", "-", nombre).strip(".-")
        if not nombre:
            nombre = "evidencia"
        return f"evidencias/{servicio_id}/{uuid4().hex}-{nombre}"
