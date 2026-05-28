from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.usuario import Usuario


class UsuarioRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def obtener_por_id(self, usuario_id: int) -> Usuario | None:
        return await self.session.get(Usuario, usuario_id)

    async def obtener_por_correo(self, correo: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.correo == correo)
        return await self.session.scalar(stmt)

    async def crear(self, usuario: Usuario) -> Usuario:
        self.session.add(usuario)
        await self.session.commit()
        await self.session.refresh(usuario)
        return usuario

