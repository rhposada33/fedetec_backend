from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.tipo_servicio import TipoServicio
from app.repositorios.configuracion_app import ConfiguracionAppRepositorio
from app.repositorios.empresa_cliente import EmpresaClienteRepositorio
from app.repositorios.evidencia_servicio import EvidenciaServicioRepositorio
from app.repositorios.servicio import ServicioRepositorio
from app.repositorios.tecnico import TecnicoRepositorio
from app.repositorios.tipo_servicio import TipoServicioRepositorio
from app.schemas.admin import (
    ConfiguracionActualizar,
    ConfiguracionAprobacionEvidenciasLeer,
    ConfiguracionLeer,
    DashboardEstadoMetrica,
    DashboardLeer,
)
from app.schemas.empresa_cliente import EmpresaClienteLeer
from app.schemas.evidencia_servicio import EvidenciaServicioLeer
from app.schemas.servicio import ServicioLeer
from app.schemas.tecnico import (
    MetricasRendimientoTecnicoLeer,
    TecnicoActualizar,
    TecnicoLeer,
)
from app.schemas.tipo_servicio import (
    TipoServicioActualizar,
    TipoServicioCrear,
    TipoServicioLeer,
)
from app.servicios.evidencia_servicio import CONFIG_APROBACION_EVIDENCIAS
from app.servicios.servicio import ServicioServicio
from app.servicios.tecnico import TecnicoServicio


class AdminServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.configuracion = ConfiguracionAppRepositorio(session)
        self.empresas = EmpresaClienteRepositorio(session)
        self.evidencias = EvidenciaServicioRepositorio(session)
        self.servicios = ServicioRepositorio(session)
        self.tecnicos = TecnicoRepositorio(session)
        self.tipos_servicio = TipoServicioRepositorio(session)

    async def dashboard(
        self,
        estado: str | None = None,
        empresa_cliente_id: UUID | None = None,
        tecnico_id: UUID | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> DashboardLeer:
        metricas = await self.servicios.contar_por_estado(
            estado, empresa_cliente_id, tecnico_id, fecha_desde, fecha_hasta
        )
        total = sum(metricas.values())
        return DashboardLeer(
            total_servicios=total,
            servicios_por_estado=[
                DashboardEstadoMetrica(estado=estado, total=total)
                for estado, total in sorted(metricas.items())
            ],
        )

    async def listar_servicios(
        self,
        estado: str | None = None,
        empresa_cliente_id: UUID | None = None,
        tecnico_id: UUID | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[ServicioLeer]:
        servicios = await self.servicios.listar_admin(
            estado, empresa_cliente_id, tecnico_id, fecha_desde, fecha_hasta
        )
        return [ServicioServicio._serializar(servicio) for servicio in servicios]

    async def listar_tecnicos(self, esta_disponible: bool | None = None) -> list[TecnicoLeer]:
        tecnicos = await self.tecnicos.listar_admin(esta_disponible)
        return [TecnicoServicio._serializar(tecnico) for tecnico in tecnicos]

    async def actualizar_tecnico(
        self, tecnico_id: UUID, tecnico_in: TecnicoActualizar
    ) -> TecnicoLeer | None:
        return await TecnicoServicio(self.session).actualizar_admin(tecnico_id, tecnico_in)

    async def obtener_metricas_tecnico(
        self, tecnico_id: UUID
    ) -> MetricasRendimientoTecnicoLeer | None:
        return await TecnicoServicio(self.session).obtener_metricas_rendimiento(tecnico_id)

    async def listar_empresas_cliente(
        self, esta_activa: bool | None = None
    ) -> list[EmpresaClienteLeer]:
        empresas = await self.empresas.listar_admin(esta_activa)
        return [
            EmpresaClienteLeer.model_validate(empresa, from_attributes=True)
            for empresa in empresas
        ]

    async def listar_evidencias_pendientes(self) -> list[EvidenciaServicioLeer]:
        evidencias = await self.evidencias.listar_pendientes()
        return [
            EvidenciaServicioLeer.model_validate(evidencia, from_attributes=True)
            for evidencia in evidencias
        ]

    async def actualizar_configuracion(
        self, configuracion_in: ConfiguracionActualizar
    ) -> ConfiguracionLeer:
        configuracion = await self.configuracion.guardar_valor(
            CONFIG_APROBACION_EVIDENCIAS,
            configuracion_in.aprobacion_evidencias.model_dump(),
        )
        return ConfiguracionLeer(
            aprobacion_evidencias=ConfiguracionAprobacionEvidenciasLeer.model_validate(
                configuracion.valor
            ),
            fecha_actualizacion=configuracion.fecha_actualizacion,
        )

    async def listar_tipos_servicio(self, solo_activos: bool = False) -> list[TipoServicioLeer]:
        tipos = await self.tipos_servicio.listar(solo_activos)
        return [TipoServicioLeer.model_validate(tipo) for tipo in tipos]

    async def crear_tipo_servicio(self, tipo_in: TipoServicioCrear) -> TipoServicioLeer:
        tipo = TipoServicio(**tipo_in.model_dump())
        creado = await self.tipos_servicio.crear(tipo)
        return TipoServicioLeer.model_validate(creado)

    async def actualizar_tipo_servicio(
        self, tipo_servicio_id: int, tipo_in: TipoServicioActualizar
    ) -> TipoServicioLeer | None:
        tipo = await self.tipos_servicio.obtener_por_id(tipo_servicio_id)
        if tipo is None:
            return None

        datos = tipo_in.model_dump(exclude_unset=True)
        for campo, valor in datos.items():
            setattr(tipo, campo, valor)

        actualizado = await self.tipos_servicio.guardar(tipo)
        return TipoServicioLeer.model_validate(actualizado)

    async def desactivar_tipo_servicio(self, tipo_servicio_id: int) -> TipoServicioLeer | None:
        tipo = await self.tipos_servicio.obtener_por_id(tipo_servicio_id)
        if tipo is None:
            return None
        tipo.esta_activo = False
        actualizado = await self.tipos_servicio.guardar(tipo)
        return TipoServicioLeer.model_validate(actualizado)
