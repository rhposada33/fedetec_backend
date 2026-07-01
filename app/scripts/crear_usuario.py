from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.correo import servicio_correo
from app.core.database import AsyncSessionLocal
from app.core.security import generar_password_hash
from app.modelos.empresa_cliente import EmpresaCliente
from app.modelos.rol import Rol
from app.modelos.tecnico import Tecnico
from app.modelos.usuario import Usuario
from app.modelos.usuario_rol import UsuarioRol

ROLES_VALIDOS = ("ADMIN", "TECNICO", "EMPRESA_CLIENTE")
CORREOS_DEMO_LEGACY = {
    "admin@fedetec.test": "admin@fedetec.dev",
    "tecnico@fedetec.test": "tecnico@fedetec.dev",
    "empresa@fedetec.test": "empresa@fedetec.dev",
}


@dataclass(frozen=True)
class UsuarioSeed:
    correo: str
    password: str
    nombre: str
    roles: tuple[str, ...]
    telefono: str | None = None
    identificacion_tributaria: str | None = None


async def obtener_o_crear_rol(session: AsyncSession, nombre: str) -> Rol:
    rol = await session.scalar(select(Rol).where(Rol.nombre == nombre))
    if rol is not None:
        return rol

    rol = Rol(nombre=nombre)
    session.add(rol)
    await session.flush()
    return rol


async def obtener_usuario(session: AsyncSession, correo: str) -> Usuario | None:
    return await session.scalar(select(Usuario).where(Usuario.correo == correo))


async def migrar_correo_demo_legacy(session: AsyncSession, correo: str) -> None:
    correo_legacy = next(
        (legacy for legacy, actual in CORREOS_DEMO_LEGACY.items() if actual == correo),
        None,
    )
    if correo_legacy is None:
        return

    usuario_actual = await obtener_usuario(session, correo)
    usuario_legacy = await obtener_usuario(session, correo_legacy)
    if usuario_actual is None and usuario_legacy is not None:
        usuario_legacy.correo = correo
        await session.flush()


async def obtener_roles_usuario(session: AsyncSession, usuario: Usuario) -> set[str]:
    resultado = await session.scalars(
        select(Rol.nombre)
        .join(UsuarioRol, UsuarioRol.rol_id == Rol.id)
        .where(UsuarioRol.usuario_id == usuario.id)
    )
    return set(resultado.all())


async def usuario_tiene_tecnico(session: AsyncSession, usuario: Usuario) -> bool:
    tecnico_id = await session.scalar(
        select(Tecnico.id).where(Tecnico.usuario_id == usuario.id).limit(1)
    )
    return tecnico_id is not None


async def obtener_empresa_por_usuario(
    session: AsyncSession, usuario: Usuario
) -> EmpresaCliente | None:
    return await session.scalar(
        select(EmpresaCliente).where(EmpresaCliente.usuario_id == usuario.id)
    )


async def crear_o_actualizar_empresa_cliente(
    session: AsyncSession, usuario: Usuario, seed: UsuarioSeed
) -> None:
    empresa = await obtener_empresa_por_usuario(session, usuario)
    if empresa is None:
        session.add(
            EmpresaCliente(
                usuario_id=usuario.id,
                nombre=seed.nombre,
                identificacion_tributaria=seed.identificacion_tributaria,
                correo_contacto=seed.correo,
                telefono_contacto=seed.telefono,
                hash_api_key=None,
                esta_activa=True,
            )
        )
        return

    empresa.nombre = seed.nombre
    empresa.identificacion_tributaria = seed.identificacion_tributaria
    empresa.correo_contacto = seed.correo
    empresa.telefono_contacto = seed.telefono
    empresa.esta_activa = True


async def crear_o_actualizar_usuario(
    session: AsyncSession,
    seed: UsuarioSeed,
    *,
    actualizar_password: bool = True,
) -> Usuario:
    await migrar_correo_demo_legacy(session, seed.correo)
    usuario = await obtener_usuario(session, seed.correo)
    usuario_nuevo = usuario is None
    password_hash = generar_password_hash(seed.password)

    if usuario is None:
        usuario = Usuario(
            nombre_completo=seed.nombre,
            correo=seed.correo,
            hash_contrasena=password_hash,
            telefono=seed.telefono,
            esta_activo=True,
        )
        session.add(usuario)
        await session.flush()
    else:
        usuario.nombre_completo = seed.nombre
        usuario.telefono = seed.telefono
        usuario.esta_activo = True
        if actualizar_password:
            usuario.hash_contrasena = password_hash

    roles_actuales = await obtener_roles_usuario(session, usuario)
    for nombre_rol in seed.roles:
        if nombre_rol in roles_actuales:
            continue
        rol = await obtener_o_crear_rol(session, nombre_rol)
        session.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol.id))

    if "TECNICO" in seed.roles and not await usuario_tiene_tecnico(session, usuario):
        session.add(Tecnico(usuario_id=usuario.id, esta_disponible=True))

    if "EMPRESA_CLIENTE" in seed.roles:
        await crear_o_actualizar_empresa_cliente(session, usuario, seed)

    await session.commit()
    await session.refresh(usuario)
    if usuario_nuevo:
        await servicio_correo.enviar_bienvenida(usuario.correo, usuario.nombre_completo)
    return usuario


async def crear_demo(password: str, actualizar_password: bool) -> list[Usuario]:
    seeds = [
        UsuarioSeed(
            correo="admin@fedetec.dev",
            password=password,
            nombre="Admin Fedetec Test",
            roles=("ADMIN",),
        ),
        UsuarioSeed(
            correo="tecnico@fedetec.dev",
            password=password,
            nombre="Tecnico Fedetec Test",
            roles=("TECNICO",),
            telefono="+57 300 000 0000",
        ),
        UsuarioSeed(
            correo="empresa@fedetec.dev",
            password=password,
            nombre="Empresa Fedetec Test",
            roles=("EMPRESA_CLIENTE",),
            telefono="+57 301 000 0000",
            identificacion_tributaria="900000001",
        ),
    ]

    async with AsyncSessionLocal() as session:
        usuarios: list[Usuario] = []
        for seed in seeds:
            usuarios.append(
                await crear_o_actualizar_usuario(
                    session,
                    seed,
                    actualizar_password=actualizar_password,
                )
            )
        return usuarios


async def crear_unico(args: argparse.Namespace) -> Usuario:
    seed = UsuarioSeed(
        correo=args.correo,
        password=args.password,
        nombre=args.nombre,
        roles=tuple(args.rol),
        telefono=args.telefono,
        identificacion_tributaria=args.identificacion_tributaria,
    )
    async with AsyncSessionLocal() as session:
        return await crear_o_actualizar_usuario(
            session,
            seed,
            actualizar_password=not args.no_reset_password,
        )


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crea o actualiza usuarios locales para pruebas manuales."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Crea admin@fedetec.dev, tecnico@fedetec.dev y empresa@fedetec.dev.",
    )
    parser.add_argument(
        "--empresa",
        action="store_true",
        help="Crea o actualiza un usuario EMPRESA_CLIENTE con empresa cliente vinculada.",
    )
    parser.add_argument(
        "--correo",
        help="Correo del usuario a crear o actualizar.",
    )
    parser.add_argument(
        "--password",
        default="Fedetec123!",
        help="Password a guardar. Por defecto: Fedetec123!",
    )
    parser.add_argument(
        "--nombre",
        default="Usuario Fedetec",
        help="Nombre completo del usuario.",
    )
    parser.add_argument(
        "--rol",
        action="append",
        choices=ROLES_VALIDOS,
        default=[],
        help="Rol del usuario. Puede repetirse.",
    )
    parser.add_argument("--telefono", help="Telefono opcional.")
    parser.add_argument(
        "--identificacion-tributaria",
        help="NIT o identificacion tributaria para usuarios empresa.",
    )
    parser.add_argument(
        "--no-reset-password",
        action="store_true",
        help="No cambia el password si el usuario ya existe.",
    )
    return parser


async def ejecutar(args: argparse.Namespace) -> None:
    if args.demo:
        usuarios = await crear_demo(args.password, actualizar_password=not args.no_reset_password)
        for usuario in usuarios:
            print(f"OK {usuario.correo}")
        return

    if not args.correo:
        raise SystemExit("Debes usar --correo o --demo.")

    if not args.rol:
        args.rol = ["EMPRESA_CLIENTE"] if args.empresa else ["ADMIN"]
    if args.empresa and "EMPRESA_CLIENTE" not in args.rol:
        args.rol.append("EMPRESA_CLIENTE")

    usuario = await crear_unico(args)
    print(f"OK {usuario.correo}")


def main() -> None:
    parser = construir_parser()
    args = parser.parse_args()
    asyncio.run(ejecutar(args))


if __name__ == "__main__":
    main()
