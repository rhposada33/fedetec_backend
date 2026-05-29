from datetime import UTC, datetime
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy.exc import IntegrityError
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
    MetricasRendimientoTecnicoLeer,
    NotificacionServicioTecnicoLeer,
    TecnicoActualizar,
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

    async def actualizar_admin(
        self, tecnico_id: UUID, tecnico_in: TecnicoActualizar
    ) -> TecnicoLeer | None:
        tecnico_con_ubicacion = await self.tecnicos.obtener_por_id(tecnico_id)
        if tecnico_con_ubicacion is None:
            return None

        tecnico = tecnico_con_ubicacion.tecnico
        usuario = tecnico.usuario
        datos = tecnico_in.model_dump(exclude_unset=True)
        for campo in [
            "nombre_completo",
            "correo",
            "telefono",
            "numero_documento",
            "ciudad",
            "municipio",
            "direccion",
            "eps",
            "arl",
            "tiene_vehiculo",
            "placa_vehiculo",
            "esta_activo",
        ]:
            if campo in datos:
                setattr(usuario, campo, datos[campo])

        if "esta_disponible" in datos:
            tecnico.esta_disponible = tecnico_in.esta_disponible

        if "latitud" in datos or "longitud" in datos:
            if tecnico_in.latitud is None or tecnico_in.longitud is None:
                raise ValueError("latitud y longitud son requeridas para actualizar ubicacion")
            tecnico.ubicacion_actual = WKTElement(
                f"POINT({tecnico_in.longitud} {tecnico_in.latitud})", srid=4326
            )
            tecnico.fecha_ultima_ubicacion = datetime.now(UTC)

        try:
            await self.tecnicos.guardar(tecnico)
        except IntegrityError as exc:
            await self.tecnicos.session.rollback()
            raise ValueError("Ya existe un usuario con ese correo") from exc

        actualizado = await self.tecnicos.obtener_por_id(tecnico_id)
        if actualizado is None:
            raise RuntimeError("No fue posible recuperar el tecnico actualizado")
        return self._serializar(actualizado)

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

    async def obtener_metricas_rendimiento(
        self, tecnico_id: UUID
    ) -> MetricasRendimientoTecnicoLeer | None:
        tecnico = await self.tecnicos.obtener_por_id(tecnico_id)
        if tecnico is None:
            return None
        metricas = await self.tecnicos.obtener_metricas_rendimiento(tecnico_id)
        return MetricasRendimientoTecnicoLeer(
            tecnico_id=tecnico_id,
            calificacion_promedio=metricas.calificacion_promedio,
            servicios_completados=metricas.servicios_completados,
            servicios_aceptados=metricas.servicios_aceptados,
            servicios_rechazados=metricas.servicios_rechazados,
        )

    @staticmethod
    def _serializar(tecnico_con_ubicacion: TecnicoConUbicacion) -> TecnicoLeer:
        tecnico = tecnico_con_ubicacion.tecnico
        return TecnicoLeer(
            id=tecnico.id,
            usuario_id=tecnico.usuario_id,
            nombre_completo=tecnico.usuario.nombre_completo,
            correo=tecnico.usuario.correo,
            telefono=tecnico.usuario.telefono,
            numero_documento=tecnico.usuario.numero_documento,
            ciudad=tecnico.usuario.ciudad,
            municipio=tecnico.usuario.municipio,
            direccion=tecnico.usuario.direccion,
            eps=tecnico.usuario.eps,
            arl=tecnico.usuario.arl,
            tiene_vehiculo=tecnico.usuario.tiene_vehiculo,
            placa_vehiculo=tecnico.usuario.placa_vehiculo,
            esta_activo=tecnico.usuario.esta_activo,
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
