from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.modelos.empresa_cliente import EmpresaCliente
from app.modelos.evidencia_servicio import EvidenciaServicio
from app.modelos.notificacion_servicio import NotificacionServicio
from app.modelos.servicio import Servicio
from app.modelos.tecnico import Tecnico
from app.modelos.usuario import Usuario
from app.scripts.crear_usuario import crear_demo

DEMO_PASSWORD = "Fedetec123!"
DEMO_LAT = 4.711
DEMO_LNG = -74.0721
DEMO_ADDRESS = "Bogota, Colombia"


@dataclass(frozen=True)
class ServicioDemoSpec:
    clave_idempotencia: str
    estado: str
    tipo_servicio: int
    placa_vehiculo: str
    direccion: str
    fecha_offset_horas: int
    requiere_notificacion: bool
    asignado: bool
    con_evidencia: bool = False


SERVICIOS_DEMO = [
    ServicioDemoSpec(
        clave_idempotencia="fedetec-demo-creado",
        estado="CREADO",
        tipo_servicio=1,
        placa_vehiculo="DEMO-001",
        direccion=f"{DEMO_ADDRESS} - creado",
        fecha_offset_horas=2,
        requiere_notificacion=False,
        asignado=False,
    ),
    ServicioDemoSpec(
        clave_idempotencia="fedetec-demo-disponible",
        estado="DISPONIBLE",
        tipo_servicio=2,
        placa_vehiculo="DEMO-002",
        direccion=f"{DEMO_ADDRESS} - disponible",
        fecha_offset_horas=3,
        requiere_notificacion=True,
        asignado=False,
    ),
    ServicioDemoSpec(
        clave_idempotencia="fedetec-demo-aceptado",
        estado="ACEPTADO",
        tipo_servicio=3,
        placa_vehiculo="DEMO-003",
        direccion=f"{DEMO_ADDRESS} - aceptado",
        fecha_offset_horas=4,
        requiere_notificacion=True,
        asignado=True,
    ),
    ServicioDemoSpec(
        clave_idempotencia="fedetec-demo-en-proceso",
        estado="EN_PROCESO",
        tipo_servicio=1,
        placa_vehiculo="DEMO-004",
        direccion=f"{DEMO_ADDRESS} - en proceso",
        fecha_offset_horas=5,
        requiere_notificacion=True,
        asignado=True,
    ),
    ServicioDemoSpec(
        clave_idempotencia="fedetec-demo-finalizado",
        estado="FINALIZADO",
        tipo_servicio=2,
        placa_vehiculo="DEMO-005",
        direccion=f"{DEMO_ADDRESS} - finalizado",
        fecha_offset_horas=-24,
        requiere_notificacion=True,
        asignado=True,
        con_evidencia=True,
    ),
]


async def _usuario_por_correo(session, correo: str) -> Usuario:
    usuario = await session.scalar(
        select(Usuario)
        .options(selectinload(Usuario.tecnico), selectinload(Usuario.empresa_cliente))
        .where(Usuario.correo == correo)
    )
    if usuario is None:
        raise RuntimeError(f"No se encontro usuario demo {correo}")
    return usuario


async def _servicio_por_clave(
    session,
    empresa: EmpresaCliente,
    clave_idempotencia: str,
) -> Servicio | None:
    return await session.scalar(
        select(Servicio)
        .where(Servicio.empresa_cliente_id == empresa.id)
        .where(Servicio.clave_idempotencia == clave_idempotencia)
    )


async def _notificacion(
    session,
    servicio: Servicio,
    tecnico: Tecnico,
) -> NotificacionServicio | None:
    return await session.scalar(
        select(NotificacionServicio)
        .where(NotificacionServicio.servicio_id == servicio.id)
        .where(NotificacionServicio.tecnico_id == tecnico.id)
    )


async def _evidencia_demo(
    session,
    servicio: Servicio,
) -> EvidenciaServicio | None:
    return await session.scalar(
        select(EvidenciaServicio)
        .where(EvidenciaServicio.servicio_id == servicio.id)
        .where(EvidenciaServicio.storage_key == f"evidencias/{servicio.id}/demo-finalizado.jpg")
    )


async def preparar_demo(password: str = DEMO_PASSWORD) -> None:
    await crear_demo(password, actualizar_password=True)
    ahora = datetime.now(UTC).replace(microsecond=0)

    async with AsyncSessionLocal() as session:
        admin = await _usuario_por_correo(session, "admin@fedetec.dev")
        tecnico_usuario = await _usuario_por_correo(session, "tecnico@fedetec.dev")
        empresa_usuario = await _usuario_por_correo(session, "empresa@fedetec.dev")

        if tecnico_usuario.tecnico is None:
            raise RuntimeError("El usuario tecnico@fedetec.dev no tiene perfil tecnico")
        if empresa_usuario.empresa_cliente is None:
            raise RuntimeError("El usuario empresa@fedetec.dev no tiene empresa cliente")

        tecnico = tecnico_usuario.tecnico
        empresa = empresa_usuario.empresa_cliente

        tecnico_usuario.ciudad = "Bogota"
        tecnico_usuario.tiene_vehiculo = True
        tecnico_usuario.placa_vehiculo = "FTD-123"
        tecnico.esta_disponible = True
        tecnico.ubicacion_actual = WKTElement(f"POINT({DEMO_LNG} {DEMO_LAT})", srid=4326)
        tecnico.fecha_ultima_ubicacion = ahora

        empresa.nombre = "Rafatrack Demo"
        empresa.correo_contacto = empresa_usuario.correo
        empresa.esta_activa = True

        creados: list[Servicio] = []
        for spec in SERVICIOS_DEMO:
            servicio = await _servicio_por_clave(session, empresa, spec.clave_idempotencia)
            if servicio is None:
                servicio = Servicio(
                    empresa_cliente_id=empresa.id,
                    clave_idempotencia=spec.clave_idempotencia,
                    tipo_servicio=spec.tipo_servicio,
                    placa_vehiculo=spec.placa_vehiculo,
                    ubicacion=WKTElement(f"POINT({DEMO_LNG} {DEMO_LAT})", srid=4326),
                    direccion=spec.direccion,
                    fecha_programada=ahora + timedelta(hours=spec.fecha_offset_horas),
                )
                session.add(servicio)
                await session.flush()

            servicio.tipo_servicio = spec.tipo_servicio
            servicio.placa_vehiculo = spec.placa_vehiculo
            servicio.ubicacion = WKTElement(f"POINT({DEMO_LNG} {DEMO_LAT})", srid=4326)
            servicio.direccion = spec.direccion
            servicio.fecha_programada = ahora + timedelta(hours=spec.fecha_offset_horas)
            servicio.estado = spec.estado
            servicio.tecnico_aceptado_id = tecnico.id if spec.asignado else None
            servicio.fecha_aceptacion = ahora - timedelta(hours=1) if spec.asignado else None
            servicio.fecha_inicio = (
                ahora - timedelta(minutes=40)
                if spec.estado in {"EN_PROCESO", "FINALIZADO"}
                else None
            )
            servicio.fecha_finalizacion = (
                ahora - timedelta(minutes=10) if spec.estado == "FINALIZADO" else None
            )
            servicio.fecha_validacion = None
            servicio.fecha_pago_generado = None

            if spec.requiere_notificacion:
                notificacion = await _notificacion(session, servicio, tecnico)
                if notificacion is None:
                    notificacion = NotificacionServicio(
                        servicio_id=servicio.id,
                        tecnico_id=tecnico.id,
                    )
                    session.add(notificacion)
                notificacion.estado = "ACEPTADA" if spec.asignado else "ENVIADA"

            if spec.con_evidencia and await _evidencia_demo(session, servicio) is None:
                session.add(
                    EvidenciaServicio(
                        servicio_id=servicio.id,
                        subido_por_usuario_id=tecnico_usuario.id,
                        url_archivo="http://localhost:8000/storage/demo-finalizado.jpg",
                        storage_key=f"evidencias/{servicio.id}/demo-finalizado.jpg",
                        tipo_archivo="image/jpeg",
                        descripcion="Evidencia demo finalizada",
                        estado_aprobacion="PENDIENTE",
                    )
                )

            creados.append(servicio)

        await session.commit()

        print("Demo Fedetec lista")
        print(f"Admin: admin@fedetec.dev / {password} ({admin.id})")
        print(f"Tecnico: tecnico@fedetec.dev / {password} ({tecnico.id})")
        print(f"Empresa: empresa@fedetec.dev / {password} ({empresa.id})")
        for servicio in creados:
            print(
                f"{servicio.estado:12} {servicio.placa_vehiculo:8} "
                f"{servicio.clave_idempotencia} {servicio.id}"
            )


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepara datos idempotentes para la demo Flutter + dashboard."
    )
    parser.add_argument(
        "--password",
        default=DEMO_PASSWORD,
        help=f"Password para usuarios demo. Por defecto: {DEMO_PASSWORD}",
    )
    return parser


async def ejecutar(args: argparse.Namespace) -> None:
    await preparar_demo(args.password)


def main() -> None:
    asyncio.run(ejecutar(construir_parser().parse_args()))


if __name__ == "__main__":
    main()
