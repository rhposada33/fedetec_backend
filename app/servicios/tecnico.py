from datetime import UTC, datetime

from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.tecnico import Tecnico
from app.repositorios.notificacion_servicio import (
    NotificacionServicioConUbicacion,
    NotificacionServicioRepositorio,
)
from app.repositorios.tecnico import TecnicoConUbicacion, TecnicoRepositorio
from app.schemas.servicio import ServicioLeer
from app.schemas.tecnico import (
    DisponibilidadTecnicoActualizar,
    NotificacionServicioTecnicoLeer,
    TecnicoCercanoLeer,
    TecnicoLeer,
    UbicacionTecnicoActualizar,
)


class TecnicoServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.tecnicos = TecnicoRepositorio(session)
        self.notificaciones = NotificacionServicioRepositorio(session)

    async def obtener_yo(self, tecnico: Tecnico) -> TecnicoLeer:
        tecnico_con_ubicacion = await self.tecnicos.obtener_por_id(tecnico.id)
        if tecnico_con_ubicacion is None:
            raise RuntimeError("No fue posible recuperar el tecnico actual")
        return self._serializar(tecnico_con_ubicacion)

    async def actualizar_ubicacion(
        self, tecnico: Tecnico, ubicacion_in: UbicacionTecnicoActualizar
    ) -> TecnicoLeer:
        tecnico.ubicacion_actual = WKTElement(
            f"POINT({ubicacion_in.longitud} {ubicacion_in.latitud})", srid=4326
        )
        tecnico.fecha_ultima_ubicacion = datetime.now(UTC)
        await self.tecnicos.guardar(tecnico)
        return await self.obtener_yo(tecnico)

    async def actualizar_disponibilidad(
        self, tecnico: Tecnico, disponibilidad_in: DisponibilidadTecnicoActualizar
    ) -> TecnicoLeer:
        tecnico.esta_disponible = disponibilidad_in.esta_disponible
        await self.tecnicos.guardar(tecnico)
        return await self.obtener_yo(tecnico)

    async def buscar_cercanos(
        self, latitud: float, longitud: float, radio_metros: int
    ) -> list[TecnicoCercanoLeer]:
        tecnicos = await self.tecnicos.buscar_cercanos(latitud, longitud, radio_metros)
        return [
            TecnicoCercanoLeer(
                **self._serializar(tecnico).model_dump(),
                distancia_metros=tecnico.distancia_metros or 0,
            )
            for tecnico in tecnicos
        ]

    async def listar_servicios_disponibles(self, tecnico: Tecnico) -> list[ServicioLeer]:
        notificaciones = await self.notificaciones.listar_servicios_disponibles_para_tecnico(
            tecnico.id
        )
        return [self._serializar_servicio(notificacion) for notificacion in notificaciones]

    async def listar_notificaciones(
        self, tecnico: Tecnico
    ) -> list[NotificacionServicioTecnicoLeer]:
        notificaciones = await self.notificaciones.listar_para_tecnico(tecnico.id)
        return [
            NotificacionServicioTecnicoLeer(
                id=notificacion.notificacion.id,
                servicio_id=notificacion.notificacion.servicio_id,
                tecnico_id=notificacion.notificacion.tecnico_id,
                estado=notificacion.notificacion.estado,
                fecha_envio=notificacion.notificacion.fecha_envio,
                fecha_lectura=notificacion.notificacion.fecha_lectura,
                servicio=self._serializar_servicio(notificacion),
            )
            for notificacion in notificaciones
        ]

    @staticmethod
    def _serializar(tecnico_con_ubicacion: TecnicoConUbicacion) -> TecnicoLeer:
        tecnico = tecnico_con_ubicacion.tecnico
        return TecnicoLeer(
            id=tecnico.id,
            usuario_id=tecnico.usuario_id,
            nombre_completo=tecnico.usuario.nombre_completo,
            correo=tecnico.usuario.correo,
            telefono=tecnico.usuario.telefono,
            esta_disponible=tecnico.esta_disponible,
            latitud=tecnico_con_ubicacion.latitud,
            longitud=tecnico_con_ubicacion.longitud,
            fecha_ultima_ubicacion=tecnico.fecha_ultima_ubicacion,
            fecha_creacion=tecnico.fecha_creacion,
        )

    @staticmethod
    def _serializar_servicio(
        notificacion_con_ubicacion: NotificacionServicioConUbicacion,
    ) -> ServicioLeer:
        servicio = notificacion_con_ubicacion.notificacion.servicio
        return ServicioLeer(
            id=servicio.id,
            empresa_cliente_id=servicio.empresa_cliente_id,
            tipo_servicio=servicio.tipo_servicio,
            placa_vehiculo=servicio.placa_vehiculo,
            latitud=notificacion_con_ubicacion.latitud,
            longitud=notificacion_con_ubicacion.longitud,
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
