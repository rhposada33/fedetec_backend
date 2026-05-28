from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.empresa_cliente import EmpresaCliente


class EmpresaClienteRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def listar(self) -> list[EmpresaCliente]:
        stmt = select(EmpresaCliente).order_by(EmpresaCliente.nombre)
        return list(await self.session.scalars(stmt))

    async def listar_activas_con_api_key(self) -> list[EmpresaCliente]:
        stmt = (
            select(EmpresaCliente)
            .where(EmpresaCliente.esta_activa.is_(True))
            .where(EmpresaCliente.hash_api_key.is_not(None))
        )
        return list(await self.session.scalars(stmt))

    async def obtener_por_id(self, empresa_id: UUID) -> EmpresaCliente | None:
        return await self.session.get(EmpresaCliente, empresa_id)

    async def crear(self, empresa: EmpresaCliente) -> EmpresaCliente:
        self.session.add(empresa)
        await self.session.commit()
        await self.session.refresh(empresa)
        return empresa

    async def guardar(self, empresa: EmpresaCliente) -> EmpresaCliente:
        await self.session.commit()
        await self.session.refresh(empresa)
        return empresa
