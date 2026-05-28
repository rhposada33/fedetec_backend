from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import generar_password_hash
from app.modelos.rol import Rol
from app.modelos.tecnico import Tecnico
from app.modelos.usuario import Usuario
from app.modelos.usuario_rol import UsuarioRol

ROLES_VALIDOS = ("ADMIN", "TECNICO", "EMPRESA_CLIENTE")


@dataclass(frozen=True)
class UsuarioSeed:
    correo: str
    password: str
    nombre: str
    roles: tuple[str, ...]
    telefono: str | None = None


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


async def crear_o_actualizar_usuario(
    session: AsyncSession,
    seed: UsuarioSeed,
    *,
    actualizar_password: bool = True,
) -> Usuario:
    usuario = await obtener_usuario(session, seed.correo)
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

    await session.commit()
    await session.refresh(usuario)
    return usuario


async def crear_demo(password: str, actualizar_password: bool) -> list[Usuario]:
    seeds = [
        UsuarioSeed(
            correo="admin@fedetec.test",
            password=password,
            nombre="Admin Fedetec Test",
            roles=("ADMIN",),
        ),
        UsuarioSeed(
            correo="tecnico@fedetec.test",
            password=password,
            nombre="Tecnico Fedetec Test",
            roles=("TECNICO",),
            telefono="+57 300 000 0000",
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
        help="Crea admin@fedetec.test y tecnico@fedetec.test.",
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
        args.rol = ["ADMIN"]

    usuario = await crear_unico(args)
    print(f"OK {usuario.correo}")


def main() -> None:
    parser = construir_parser()
    args = parser.parse_args()
    asyncio.run(ejecutar(args))


if __name__ == "__main__":
    main()
