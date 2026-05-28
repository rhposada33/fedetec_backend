from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generar_api_key, generar_api_key_hash
from app.modelos.empresa_cliente import EmpresaCliente
from app.repositorios.empresa_cliente import EmpresaClienteRepositorio
from app.schemas.empresa_cliente import EmpresaClienteActualizar, EmpresaClienteCrear


class EmpresaClienteServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.empresas = EmpresaClienteRepositorio(session)

    async def listar(self) -> list[EmpresaCliente]:
        return await self.empresas.listar()

    async def obtener(self, empresa_id: UUID) -> EmpresaCliente | None:
        return await self.empresas.obtener_por_id(empresa_id)

    async def crear(self, empresa_in: EmpresaClienteCrear) -> tuple[EmpresaCliente, str]:
        api_key = generar_api_key()
        empresa = EmpresaCliente(
            nombre=empresa_in.nombre,
            identificacion_tributaria=empresa_in.identificacion_tributaria,
            correo_contacto=str(empresa_in.correo_contacto) if empresa_in.correo_contacto else None,
            telefono_contacto=empresa_in.telefono_contacto,
            esta_activa=empresa_in.esta_activa,
            hash_api_key=generar_api_key_hash(api_key),
        )
        empresa = await self.empresas.crear(empresa)
        return empresa, api_key

    async def actualizar(
        self, empresa_id: UUID, empresa_in: EmpresaClienteActualizar
    ) -> EmpresaCliente | None:
        empresa = await self.empresas.obtener_por_id(empresa_id)
        if empresa is None:
            return None

        datos = empresa_in.model_dump(exclude_unset=True)
        if "correo_contacto" in datos and datos["correo_contacto"] is not None:
            datos["correo_contacto"] = str(datos["correo_contacto"])

        for campo, valor in datos.items():
            setattr(empresa, campo, valor)

        return await self.empresas.guardar(empresa)
