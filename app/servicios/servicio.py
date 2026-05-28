from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.empresa_cliente import EmpresaCliente
from app.modelos.servicio import Servicio
from app.repositorios.servicio import ServicioConUbicacion, ServicioRepositorio
from app.schemas.servicio import ServicioCrear, ServicioLeer


class ServicioServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.servicios = ServicioRepositorio(session)

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
