from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generar_password_hash
from app.modelos.empresa_cliente import EmpresaCliente
from app.modelos.rol import Rol
from app.modelos.usuario import Usuario
from app.modelos.usuario_rol import UsuarioRol
from app.repositorios.empresa_cliente import EmpresaClienteRepositorio
from app.repositorios.usuario import UsuarioRepositorio
from app.schemas.empresa_cliente import EmpresaClienteActualizar, EmpresaClienteCrear

ROL_EMPRESA_CLIENTE = "EMPRESA_CLIENTE"


class EmpresaClienteServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.empresas = EmpresaClienteRepositorio(session)
        self.usuarios = UsuarioRepositorio(session)

    async def listar(self) -> list[EmpresaCliente]:
        return await self.empresas.listar()

    async def obtener(self, empresa_id: UUID) -> EmpresaCliente | None:
        return await self.empresas.obtener_por_id(empresa_id)

    async def crear(self, empresa_in: EmpresaClienteCrear) -> EmpresaCliente:
        if empresa_in.correo_contacto is None:
            raise ValueError("El correo de contacto es requerido para crear el login")

        correo = str(empresa_in.correo_contacto)
        existente = await self.usuarios.obtener_por_correo(correo)
        if existente is not None:
            raise ValueError("Ya existe un usuario con ese correo")

        rol_empresa = await self._obtener_rol_empresa()
        usuario = Usuario(
            correo=correo,
            nombre_completo=empresa_in.nombre,
            hash_contrasena=generar_password_hash(empresa_in.password),
            telefono=empresa_in.telefono_contacto,
        )
        empresa = EmpresaCliente(
            nombre=empresa_in.nombre,
            identificacion_tributaria=empresa_in.identificacion_tributaria,
            correo_contacto=correo,
            telefono_contacto=empresa_in.telefono_contacto,
            esta_activa=empresa_in.esta_activa,
            hash_api_key=None,
            usuario=usuario,
        )
        usuario_rol = UsuarioRol(usuario=usuario, rol=rol_empresa)
        self.session.add_all([usuario, empresa, usuario_rol])
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError("No fue posible crear la empresa cliente") from exc

        await self.session.refresh(empresa)
        return empresa

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

        if empresa.usuario_id is not None:
            usuario = await self.session.get(Usuario, empresa.usuario_id)
            if usuario is not None:
                if "nombre" in datos:
                    usuario.nombre_completo = empresa.nombre
                if "correo_contacto" in datos and datos["correo_contacto"] is not None:
                    usuario.correo = datos["correo_contacto"]
                if "telefono_contacto" in datos:
                    usuario.telefono = empresa.telefono_contacto
                if "esta_activa" in datos:
                    usuario.esta_activo = empresa.esta_activa

        try:
            return await self.empresas.guardar(empresa)
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError("No fue posible actualizar la empresa cliente") from exc

    async def _obtener_rol_empresa(self) -> Rol:
        rol = await self.session.scalar(select(Rol).where(Rol.nombre == ROL_EMPRESA_CLIENTE))
        if rol is None:
            rol = Rol(nombre=ROL_EMPRESA_CLIENTE)
            self.session.add(rol)
            await self.session.flush()
        return rol
