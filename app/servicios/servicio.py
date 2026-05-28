from datetime import UTC, datetime
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.empresa_cliente import EmpresaCliente
from app.modelos.reprogramacion_servicio import ReprogramacionServicio
from app.modelos.servicio import Servicio
from app.modelos.tecnico import Tecnico
from app.repositorios.notificacion_servicio import NotificacionServicioRepositorio
from app.repositorios.rechazo_servicio import RechazoServicioRepositorio
from app.repositorios.reprogramacion_servicio import ReprogramacionServicioRepositorio
from app.repositorios.servicio import ServicioConUbicacion, ServicioRepositorio
from app.repositorios.tecnico import TecnicoRepositorio
from app.schemas.servicio import (
    ReprogramacionServicioLeer,
    ServicioCrear,
    ServicioLeer,
    ServicioPublicadoLeer,
    ServicioRechazadoLeer,
    ServicioRechazar,
    ServicioReprogramar,
)


class ServicioServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.servicios = ServicioRepositorio(session)
        self.tecnicos = TecnicoRepositorio(session)
        self.notificaciones = NotificacionServicioRepositorio(session)
        self.rechazos = RechazoServicioRepositorio(session)
        self.reprogramaciones = ReprogramacionServicioRepositorio(session)

    async def crear(
        self,
        servicio_in: ServicioCrear,
        empresa_cliente: EmpresaCliente,
        clave_idempotencia: str,
    ) -> ServicioLeer:
        servicio = Servicio(
            empresa_cliente_id=empresa_cliente.id,
            tipo_servicio=servicio_in.tipo_servicio,
            placa_vehiculo=servicio_in.placa_vehiculo,
            ubicacion=WKTElement(
                f"POINT({servicio_in.longitud} {servicio_in.latitud})", srid=4326
            ),
            direccion=servicio_in.direccion,
            fecha_programada=servicio_in.fecha_programada,
            estado="CREADO",
            clave_idempotencia=clave_idempotencia,
        )
        creado = await self.servicios.crear_idempotente(servicio, clave_idempotencia)
        return self._serializar(creado)

    async def listar(self, empresa_cliente: EmpresaCliente) -> list[ServicioLeer]:
        servicios = await self.servicios.listar_por_empresa(empresa_cliente.id)
        return [self._serializar(servicio) for servicio in servicios]

    async def listar_admin(self) -> list[ServicioLeer]:
        servicios = await self.servicios.listar_admin()
        return [self._serializar(servicio) for servicio in servicios]

    async def obtener(
        self, servicio_id: UUID, empresa_cliente: EmpresaCliente
    ) -> ServicioLeer | None:
        servicio = await self.servicios.obtener_por_id_y_empresa(servicio_id, empresa_cliente.id)
        return self._serializar(servicio) if servicio is not None else None

    async def obtener_admin(self, servicio_id: UUID) -> ServicioLeer | None:
        servicio = await self.servicios.obtener_por_id(servicio_id)
        return self._serializar(servicio) if servicio is not None else None

    async def publicar(
        self, servicio_id: UUID, radio_metros: int = 10_000
    ) -> ServicioPublicadoLeer | None:
        servicio_con_ubicacion = await self.servicios.obtener_por_id(servicio_id)
        if servicio_con_ubicacion is None:
            return None

        servicio = servicio_con_ubicacion.servicio
        if servicio.estado != "CREADO":
            raise ValueError("Solo se pueden publicar servicios en estado CREADO")

        tecnicos_cercanos = await self.tecnicos.buscar_cercanos(
            servicio_con_ubicacion.latitud,
            servicio_con_ubicacion.longitud,
            radio_metros,
        )
        notificaciones_creadas = await self.notificaciones.crear_para_tecnicos_una_vez(
            servicio.id,
            [tecnico.tecnico.id for tecnico in tecnicos_cercanos],
        )

        servicio.estado = "DISPONIBLE"
        await self.servicios.guardar(servicio)
        publicado = await self.servicios.obtener_por_id(servicio.id)
        if publicado is None:
            raise RuntimeError("No fue posible recuperar el servicio publicado")

        return ServicioPublicadoLeer(
            **self._serializar(publicado).model_dump(),
            notificaciones_creadas=notificaciones_creadas,
            tecnicos_cercanos=len(tecnicos_cercanos),
        )

    async def aceptar(self, servicio_id: UUID, tecnico: Tecnico) -> ServicioLeer | None:
        servicio = await self.servicios.obtener_por_id_para_actualizar(servicio_id)
        if servicio is None:
            return None
        if servicio.estado != "DISPONIBLE" or servicio.tecnico_aceptado_id is not None:
            raise ValueError("El servicio ya no esta disponible")

        servicio.estado = "ACEPTADO"
        servicio.tecnico_aceptado_id = tecnico.id
        servicio.fecha_aceptacion = datetime.now(UTC)
        await self.notificaciones.actualizar_estado_para_tecnico(
            servicio.id, tecnico.id, "ACEPTADA"
        )
        await self.session.commit()

        aceptado = await self.servicios.obtener_por_id(servicio_id)
        if aceptado is None:
            raise RuntimeError("No fue posible recuperar el servicio aceptado")
        return self._serializar(aceptado)

    async def rechazar(
        self, servicio_id: UUID, tecnico: Tecnico, rechazo_in: ServicioRechazar
    ) -> ServicioRechazadoLeer | None:
        servicio = await self.servicios.obtener_por_id(servicio_id)
        if servicio is None:
            return None

        rechazo_creado = await self.rechazos.crear_una_vez(
            servicio_id, tecnico.id, rechazo_in.motivo
        )
        await self.notificaciones.actualizar_estado_para_tecnico(
            servicio_id, tecnico.id, "RECHAZADA"
        )
        await self.session.commit()
        return ServicioRechazadoLeer(
            servicio_id=servicio_id,
            tecnico_id=tecnico.id,
            rechazo_creado=rechazo_creado,
            estado="RECHAZADO_POR_TECNICO",
        )

    async def reprogramar(
        self, servicio_id: UUID, tecnico: Tecnico, reprogramacion_in: ServicioReprogramar
    ) -> ReprogramacionServicioLeer | None:
        servicio = await self.servicios.obtener_por_id_para_actualizar(servicio_id)
        if servicio is None:
            return None
        if servicio.estado not in {"DISPONIBLE", "ACEPTADO"}:
            raise ValueError("El servicio no permite reprogramacion")

        reprogramacion = ReprogramacionServicio(
            servicio_id=servicio_id,
            tecnico_id=tecnico.id,
            fecha_propuesta=reprogramacion_in.fecha_propuesta,
            motivo=reprogramacion_in.motivo,
            estado="PENDIENTE",
        )
        await self.reprogramaciones.crear(reprogramacion)
        servicio.estado = "REPROGRAMACION_SOLICITADA"
        await self.session.commit()

        return ReprogramacionServicioLeer.model_validate(reprogramacion, from_attributes=True)

    async def iniciar(self, servicio_id: UUID, tecnico: Tecnico) -> ServicioLeer | None:
        servicio = await self.servicios.obtener_por_id_para_actualizar(servicio_id)
        if servicio is None:
            return None
        self._validar_tecnico_asignado(servicio, tecnico)
        if servicio.estado != "ACEPTADO":
            raise ValueError("Solo se pueden iniciar servicios en estado ACEPTADO")

        servicio.estado = "EN_PROCESO"
        servicio.fecha_inicio = datetime.now(UTC)
        await self.session.commit()

        iniciado = await self.servicios.obtener_por_id(servicio_id)
        if iniciado is None:
            raise RuntimeError("No fue posible recuperar el servicio iniciado")
        return self._serializar(iniciado)

    async def finalizar(self, servicio_id: UUID, tecnico: Tecnico) -> ServicioLeer | None:
        servicio = await self.servicios.obtener_por_id_para_actualizar(servicio_id)
        if servicio is None:
            return None
        self._validar_tecnico_asignado(servicio, tecnico)
        if servicio.estado != "EN_PROCESO":
            raise ValueError("Solo se pueden finalizar servicios en estado EN_PROCESO")

        servicio.estado = "FINALIZADO"
        servicio.fecha_finalizacion = datetime.now(UTC)
        await self.session.commit()

        finalizado = await self.servicios.obtener_por_id(servicio_id)
        if finalizado is None:
            raise RuntimeError("No fue posible recuperar el servicio finalizado")
        return self._serializar(finalizado)

    @staticmethod
    def _serializar(servicio_con_ubicacion: ServicioConUbicacion) -> ServicioLeer:
        servicio = servicio_con_ubicacion.servicio
        return ServicioLeer(
            id=servicio.id,
            empresa_cliente_id=servicio.empresa_cliente_id,
            tipo_servicio=servicio.tipo_servicio,
            placa_vehiculo=servicio.placa_vehiculo,
            latitud=servicio_con_ubicacion.latitud,
            longitud=servicio_con_ubicacion.longitud,
            direccion=servicio.direccion,
            fecha_programada=servicio.fecha_programada,
            estado=servicio.estado,
            clave_idempotencia=servicio.clave_idempotencia,
            tecnico_aceptado_id=servicio.tecnico_aceptado_id,
            fecha_aceptacion=servicio.fecha_aceptacion,
            fecha_inicio=servicio.fecha_inicio,
            fecha_finalizacion=servicio.fecha_finalizacion,
            fecha_creacion=servicio.fecha_creacion,
            fecha_actualizacion=servicio.fecha_actualizacion,
        )

    @staticmethod
    def _validar_tecnico_asignado(servicio: Servicio, tecnico: Tecnico) -> None:
        if servicio.tecnico_aceptado_id != tecnico.id:
            raise PermissionError("Solo el tecnico asignado puede ejecutar esta accion")
