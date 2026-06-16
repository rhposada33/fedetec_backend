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
from app.repositorios.tipo_servicio import TipoServicioRepositorio
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


class ServicioServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.servicios = ServicioRepositorio(session)
        self.tecnicos = TecnicoRepositorio(session)
        self.tipos_servicio = TipoServicioRepositorio(session)
        self.notificaciones = NotificacionServicioRepositorio(session)
        self.rechazos = RechazoServicioRepositorio(session)
        self.reprogramaciones = ReprogramacionServicioRepositorio(session)

    async def crear(
        self,
        servicio_in: ServicioCrear,
        empresa_cliente: EmpresaCliente,
        clave_idempotencia: str,
    ) -> ServicioLeer:
        tipo_servicio = await self.tipos_servicio.obtener_por_id(servicio_in.tipo_servicio)
        if tipo_servicio is None or not tipo_servicio.esta_activo:
            raise ValueError("Tipo de servicio no encontrado o inactivo")

        servicio = Servicio(
            empresa_cliente_id=empresa_cliente.id,
            tipo_servicio=tipo_servicio.id,
            tipo_servicio_nombre=tipo_servicio.nombre,
            valor_servicio=tipo_servicio.valor,
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

    async def obtener_historial_admin(
        self, servicio_id: UUID
    ) -> list[HistorialServicioEventoLeer] | None:
        servicio = await self.servicios.obtener_por_id_con_historial(servicio_id)
        return self._construir_historial(servicio) if servicio is not None else None

    async def obtener_historial_empresa(
        self, servicio_id: UUID, empresa_cliente: EmpresaCliente
    ) -> list[HistorialServicioEventoLeer] | None:
        servicio = await self.servicios.obtener_por_id_y_empresa_con_historial(
            servicio_id, empresa_cliente.id
        )
        return self._construir_historial(servicio) if servicio is not None else None

    async def actualizar(
        self,
        servicio_id: UUID,
        servicio_in: ServicioActualizar,
        empresa_cliente: EmpresaCliente | None = None,
    ) -> ServicioLeer | None:
        servicio = await self.servicios.obtener_por_id_para_actualizar(servicio_id)
        if servicio is None:
            return None
        if servicio.estado in {"FINALIZADO", "VALIDADO", "PAGO_GENERADO", "CANCELADO"}:
            raise ValueError("El servicio ya no permite edicion")

        datos = servicio_in.model_dump(exclude_unset=True)
        if "empresa_cliente_id" in datos:
            if empresa_cliente is None:
                raise ValueError("Empresa cliente no encontrada")
            servicio.empresa_cliente_id = empresa_cliente.id
        if "tipo_servicio" in datos:
            tipo_servicio = await self.tipos_servicio.obtener_por_id(servicio_in.tipo_servicio)
            if tipo_servicio is None or not tipo_servicio.esta_activo:
                raise ValueError("Tipo de servicio no encontrado o inactivo")
            servicio.tipo_servicio = tipo_servicio.id
            servicio.tipo_servicio_nombre = tipo_servicio.nombre
            servicio.valor_servicio = tipo_servicio.valor
        if "placa_vehiculo" in datos:
            servicio.placa_vehiculo = servicio_in.placa_vehiculo
        if "direccion" in datos:
            servicio.direccion = servicio_in.direccion
        if "fecha_programada" in datos:
            servicio.fecha_programada = servicio_in.fecha_programada
        if "latitud" in datos or "longitud" in datos:
            if servicio_in.latitud is None or servicio_in.longitud is None:
                raise ValueError("latitud y longitud son requeridas para actualizar ubicacion")
            servicio.ubicacion = WKTElement(
                f"POINT({servicio_in.longitud} {servicio_in.latitud})", srid=4326
            )

        await self.session.commit()
        actualizado = await self.servicios.obtener_por_id(servicio_id)
        if actualizado is None:
            raise RuntimeError("No fue posible recuperar el servicio actualizado")
        return self._serializar(actualizado)

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

    async def validar(self, servicio_id: UUID) -> ServicioLeer | None:
        servicio = await self.servicios.obtener_por_id_para_actualizar(servicio_id)
        if servicio is None:
            return None
        if servicio.estado != "FINALIZADO":
            raise ValueError("Solo se pueden validar servicios en estado FINALIZADO")

        servicio.estado = "VALIDADO"
        servicio.fecha_validacion = datetime.now(UTC)
        await self.session.commit()

        validado = await self.servicios.obtener_por_id(servicio_id)
        if validado is None:
            raise RuntimeError("No fue posible recuperar el servicio validado")
        return self._serializar(validado)

    async def reasignar(
        self, servicio_id: UUID, reasignacion_in: ServicioReasignar
    ) -> ServicioLeer | None:
        servicio = await self.servicios.obtener_por_id_para_actualizar(servicio_id)
        if servicio is None:
            return None
        if servicio.estado not in {
            "DISPONIBLE",
            "ACEPTADO",
            "REPROGRAMACION_SOLICITADA",
        }:
            raise ValueError("El servicio no permite reasignacion")

        tecnico_con_ubicacion = await self.tecnicos.obtener_por_id(reasignacion_in.tecnico_id)
        if tecnico_con_ubicacion is None:
            raise LookupError("Tecnico no encontrado")
        if not tecnico_con_ubicacion.tecnico.esta_disponible:
            raise ValueError("Solo se puede reasignar a tecnicos disponibles")

        servicio.estado = "ACEPTADO"
        servicio.tecnico_aceptado_id = tecnico_con_ubicacion.tecnico.id
        servicio.fecha_aceptacion = datetime.now(UTC)
        await self.notificaciones.crear_para_tecnicos_una_vez(
            servicio.id, [tecnico_con_ubicacion.tecnico.id]
        )
        await self.notificaciones.actualizar_estado_para_tecnico(
            servicio.id, tecnico_con_ubicacion.tecnico.id, "ACEPTADA"
        )
        await self.session.commit()

        reasignado = await self.servicios.obtener_por_id(servicio_id)
        if reasignado is None:
            raise RuntimeError("No fue posible recuperar el servicio reasignado")
        return self._serializar(reasignado)

    @staticmethod
    def _serializar(servicio_con_ubicacion: ServicioConUbicacion) -> ServicioLeer:
        servicio = servicio_con_ubicacion.servicio
        return ServicioLeer(
            id=servicio.id,
            empresa_cliente_id=servicio.empresa_cliente_id,
            tipo_servicio=servicio.tipo_servicio,
            tipo_servicio_nombre=getattr(
                servicio,
                "tipo_servicio_nombre",
                ServicioServicio._nombre_tipo_servicio_legacy(servicio.tipo_servicio),
            ),
            valor_servicio=getattr(servicio, "valor_servicio", 0),
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
            fecha_validacion=servicio.fecha_validacion,
            fecha_creacion=servicio.fecha_creacion,
            fecha_actualizacion=servicio.fecha_actualizacion,
        )

    @staticmethod
    def _nombre_tipo_servicio_legacy(tipo_servicio: int) -> str:
        return {
            1: "Mantenimiento",
            2: "Diagnostico",
            3: "Soporte vial",
        }.get(tipo_servicio, f"Tipo {tipo_servicio}")

    @staticmethod
    def _validar_tecnico_asignado(servicio: Servicio, tecnico: Tecnico) -> None:
        if servicio.tecnico_aceptado_id != tecnico.id:
            raise PermissionError("Solo el tecnico asignado puede ejecutar esta accion")

    @staticmethod
    def _construir_historial(servicio: Servicio) -> list[HistorialServicioEventoLeer]:
        eventos = [
            HistorialServicioEventoLeer(
                fecha=servicio.fecha_creacion,
                tipo_evento="SERVICIO_CREADO",
                titulo="Servicio creado",
                entidad="servicio",
                entidad_id=servicio.id,
                datos={
                    "estado": "CREADO",
                    "tipo_servicio": servicio.tipo_servicio,
                    "empresa_cliente_id": str(servicio.empresa_cliente_id),
                    "fecha_programada": servicio.fecha_programada.isoformat(),
                },
            )
        ]

        for notificacion in servicio.notificaciones:
            eventos.append(
                HistorialServicioEventoLeer(
                    fecha=notificacion.fecha_envio,
                    tipo_evento="NOTIFICACION_ENVIADA",
                    titulo="Notificacion enviada a tecnico",
                    entidad="notificacion_servicio",
                    entidad_id=notificacion.id,
                    datos={
                        "estado": notificacion.estado,
                        "tecnico_id": str(notificacion.tecnico_id),
                    },
                )
            )
            if notificacion.fecha_lectura is not None:
                eventos.append(
                    HistorialServicioEventoLeer(
                        fecha=notificacion.fecha_lectura,
                        tipo_evento="NOTIFICACION_LEIDA",
                        titulo="Notificacion leida por tecnico",
                        entidad="notificacion_servicio",
                        entidad_id=notificacion.id,
                        datos={"tecnico_id": str(notificacion.tecnico_id)},
                    )
                )

        for rechazo in servicio.rechazos:
            eventos.append(
                HistorialServicioEventoLeer(
                    fecha=rechazo.fecha_creacion,
                    tipo_evento="SERVICIO_RECHAZADO",
                    titulo="Servicio rechazado por tecnico",
                    descripcion=rechazo.motivo,
                    entidad="rechazo_servicio",
                    entidad_id=rechazo.id,
                    datos={"tecnico_id": str(rechazo.tecnico_id)},
                )
            )

        if servicio.fecha_aceptacion is not None:
            eventos.append(
                HistorialServicioEventoLeer(
                    fecha=servicio.fecha_aceptacion,
                    tipo_evento="SERVICIO_ACEPTADO",
                    titulo="Servicio aceptado",
                    entidad="servicio",
                    entidad_id=servicio.id,
                    datos={"tecnico_id": str(servicio.tecnico_aceptado_id)},
                )
            )

        for reprogramacion in servicio.reprogramaciones:
            eventos.append(
                HistorialServicioEventoLeer(
                    fecha=reprogramacion.fecha_creacion,
                    tipo_evento="REPROGRAMACION_SOLICITADA",
                    titulo="Reprogramacion solicitada",
                    descripcion=reprogramacion.motivo,
                    entidad="reprogramacion_servicio",
                    entidad_id=reprogramacion.id,
                    datos={
                        "estado": reprogramacion.estado,
                        "tecnico_id": str(reprogramacion.tecnico_id),
                        "fecha_propuesta": reprogramacion.fecha_propuesta.isoformat(),
                    },
                )
            )

        if servicio.fecha_inicio is not None:
            eventos.append(
                HistorialServicioEventoLeer(
                    fecha=servicio.fecha_inicio,
                    tipo_evento="SERVICIO_INICIADO",
                    titulo="Servicio iniciado",
                    entidad="servicio",
                    entidad_id=servicio.id,
                    datos={"tecnico_id": str(servicio.tecnico_aceptado_id)},
                )
            )

        for evidencia in servicio.evidencias:
            eventos.append(
                HistorialServicioEventoLeer(
                    fecha=evidencia.fecha_creacion,
                    tipo_evento="EVIDENCIA_SUBIDA",
                    titulo="Evidencia subida",
                    descripcion=evidencia.descripcion,
                    entidad="evidencia_servicio",
                    entidad_id=evidencia.id,
                    datos={
                        "estado_aprobacion": evidencia.estado_aprobacion,
                        "tipo_archivo": evidencia.tipo_archivo,
                        "url_archivo": evidencia.url_archivo,
                        "subido_por_usuario_id": str(evidencia.subido_por_usuario_id),
                    },
                )
            )
            if evidencia.fecha_aprobacion is not None:
                eventos.append(
                    HistorialServicioEventoLeer(
                        fecha=evidencia.fecha_aprobacion,
                        tipo_evento=f"EVIDENCIA_{evidencia.estado_aprobacion}",
                        titulo="Evidencia revisada",
                        entidad="evidencia_servicio",
                        entidad_id=evidencia.id,
                        datos={
                            "estado_aprobacion": evidencia.estado_aprobacion,
                            "aprobado_por_usuario_id": (
                                str(evidencia.aprobado_por_usuario_id)
                                if evidencia.aprobado_por_usuario_id is not None
                                else None
                            ),
                        },
                    )
                )

        if servicio.fecha_finalizacion is not None:
            eventos.append(
                HistorialServicioEventoLeer(
                    fecha=servicio.fecha_finalizacion,
                    tipo_evento="SERVICIO_FINALIZADO",
                    titulo="Servicio finalizado",
                    entidad="servicio",
                    entidad_id=servicio.id,
                    datos={"tecnico_id": str(servicio.tecnico_aceptado_id)},
                )
            )

        if servicio.fecha_validacion is not None:
            eventos.append(
                HistorialServicioEventoLeer(
                    fecha=servicio.fecha_validacion,
                    tipo_evento="SERVICIO_VALIDADO",
                    titulo="Servicio validado",
                    entidad="servicio",
                    entidad_id=servicio.id,
                )
            )

        if servicio.reporte_pago is not None:
            eventos.append(
                HistorialServicioEventoLeer(
                    fecha=servicio.reporte_pago.fecha_generacion,
                    tipo_evento="REPORTE_PAGO_GENERADO",
                    titulo="Reporte de pago generado",
                    entidad="reporte_pago",
                    entidad_id=servicio.reporte_pago.id,
                    datos={
                        "estado": servicio.reporte_pago.estado,
                        "valor": (
                            str(servicio.reporte_pago.valor)
                            if servicio.reporte_pago.valor is not None
                            else None
                        ),
                    },
                )
            )

        if servicio.fecha_pago_generado is not None:
            eventos.append(
                HistorialServicioEventoLeer(
                    fecha=servicio.fecha_pago_generado,
                    tipo_evento="SERVICIO_PAGO_GENERADO",
                    titulo="Servicio marcado para pago",
                    entidad="servicio",
                    entidad_id=servicio.id,
                )
            )

        if servicio.calificacion is not None:
            eventos.append(
                HistorialServicioEventoLeer(
                    fecha=servicio.calificacion.fecha_calificacion,
                    tipo_evento="SERVICIO_CALIFICADO",
                    titulo="Servicio calificado",
                    descripcion=servicio.calificacion.comentario,
                    entidad="calificacion_servicio",
                    entidad_id=servicio.calificacion.id,
                    datos={"puntuacion": servicio.calificacion.puntuacion},
                )
            )

        return sorted(eventos, key=lambda evento: evento.fecha)
