from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import crear_token_acceso, generar_password_hash, verificar_password
from app.modelos.usuario import Usuario
from app.repositorios.usuario import UsuarioRepositorio
from app.schemas.usuario import UsuarioCrear


class AutenticacionServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.usuarios = UsuarioRepositorio(session)

    async def registrar_usuario(self, usuario_in: UsuarioCrear) -> Usuario:
        existente = await self.usuarios.obtener_por_correo(usuario_in.correo)
        if existente is not None:
            raise ValueError("Ya existe un usuario con ese correo")

        usuario = Usuario(
            correo=usuario_in.correo,
            nombre_completo=usuario_in.nombre_completo,
            password_hash=generar_password_hash(usuario_in.password),
        )
        return await self.usuarios.crear(usuario)

    async def autenticar(self, correo: str, password: str) -> str | None:
        usuario = await self.usuarios.obtener_por_correo(correo)
        if usuario is None or not verificar_password(password, usuario.password_hash):
            return None
        return crear_token_acceso(usuario.id)

