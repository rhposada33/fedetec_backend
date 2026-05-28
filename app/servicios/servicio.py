from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.empresa_cliente import EmpresaCliente
from app.modelos.servicio import Servicio
from app.repositorios.notificacion_servicio import NotificacionServicioRepositorio
from app.repositorios.servicio import ServicioConUbicacion, ServicioRepositorio
from app.repositorios.tecnico import TecnicoRepositorio
from app.schemas.servicio import ServicioCrear, ServicioLeer, ServicioPublicadoLeer


class ServicioServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.servicios = ServicioRepositorio(session)
        self.tecnicos = TecnicoRepositorio(session)
        self.notificaciones = NotificacionServicioRepositorio(session)

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

    async def obtener(
        self, servicio_id: UUID, empresa_cliente: EmpresaCliente
    ) -> ServicioLeer | None:
        servicio = await self.servicios.obtener_por_id_y_empresa(servicio_id, empresa_cliente.id)
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
            fecha_creacion=servicio.fecha_creacion,
            fecha_actualizacion=servicio.fecha_actualizacion,
        )
