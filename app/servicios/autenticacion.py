from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.correo import servicio_correo
from app.core.security import crear_token_acceso, generar_password_hash, verificar_password
from app.modelos.rol import Rol
from app.modelos.tecnico import Tecnico
from app.modelos.usuario import Usuario
from app.modelos.usuario_rol import UsuarioRol
from app.repositorios.usuario import UsuarioRepositorio
from app.schemas.autenticacion import TecnicoRegistrar, UsuarioAutenticadoLeer
from app.schemas.usuario import UsuarioCrear

ROL_TECNICO = "TECNICO"


class AutenticacionServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.usuarios = UsuarioRepositorio(session)

    async def registrar_usuario(self, usuario_in: UsuarioCrear) -> Usuario:
        existente = await self.usuarios.obtener_por_correo(usuario_in.correo)
        if existente is not None:
            raise ValueError("Ya existe un usuario con ese correo")

        usuario = Usuario(
            correo=usuario_in.correo,
            nombre_completo=usuario_in.nombre_completo,
            hash_contrasena=generar_password_hash(usuario_in.password),
        )
        creado = await self.usuarios.crear(usuario)
        await servicio_correo.enviar_bienvenida(creado.correo, creado.nombre_completo)
        return creado

    async def registrar_tecnico(self, tecnico_in: TecnicoRegistrar) -> UsuarioAutenticadoLeer:
        existente = await self.usuarios.obtener_por_correo(tecnico_in.correo)
        if existente is not None:
            raise ValueError("Ya existe un usuario con ese correo")

        rol_tecnico = await self._obtener_rol_tecnico()
        usuario = Usuario(
            correo=tecnico_in.correo,
            nombre_completo=tecnico_in.nombre_completo,
            hash_contrasena=generar_password_hash(tecnico_in.contrasena),
            telefono=tecnico_in.telefono,
            numero_documento=tecnico_in.numero_documento,
            ciudad=tecnico_in.ciudad,
            municipio=tecnico_in.municipio,
            direccion=tecnico_in.direccion,
            eps=tecnico_in.eps,
            arl=tecnico_in.arl,
            tiene_vehiculo=tecnico_in.tiene_vehiculo,
            placa_vehiculo=tecnico_in.placa_vehiculo,
        )
        tecnico = Tecnico(usuario=usuario)
        usuario_rol = UsuarioRol(usuario=usuario, rol=rol_tecnico)

        self.session.add_all([usuario, tecnico, usuario_rol])
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError("No fue posible registrar el tecnico") from exc

        await self.session.refresh(usuario)
        await self.session.refresh(tecnico)
        await servicio_correo.enviar_bienvenida(usuario.correo, usuario.nombre_completo)
        return self._serializar_usuario_autenticado(
            usuario, roles=[ROL_TECNICO], tecnico_id=tecnico.id
        )

    async def autenticar(self, correo: str, password: str) -> str | None:
        usuario = await self.usuarios.obtener_por_correo(correo)
        if usuario is None or not verificar_password(password, usuario.hash_contrasena):
            return None
        return crear_token_acceso(usuario.id)

    async def obtener_usuario_autenticado(self, usuario_id: UUID) -> UsuarioAutenticadoLeer | None:
        usuario = await self.usuarios.obtener_por_id_con_autenticacion(usuario_id)
        if usuario is None or not usuario.esta_activo:
            return None
        return self._serializar_usuario_autenticado(usuario)

    async def _obtener_rol_tecnico(self) -> Rol:
        rol = await self.session.scalar(select(Rol).where(Rol.nombre == ROL_TECNICO))
        if rol is None:
            rol = Rol(nombre=ROL_TECNICO)
            self.session.add(rol)
            await self.session.flush()
        return rol

    @staticmethod
    def _serializar_usuario_autenticado(
        usuario: Usuario,
        roles: list[str] | None = None,
        tecnico_id: UUID | None = None,
        empresa_cliente_id: UUID | None = None,
    ) -> UsuarioAutenticadoLeer:
        nombres_roles = roles or [usuario_rol.rol.nombre for usuario_rol in usuario.roles]
        tecnico = usuario.__dict__.get("tecnico")
        empresa_cliente = usuario.__dict__.get("empresa_cliente")
        id_tecnico = tecnico_id or (tecnico.id if tecnico is not None else None)
        id_empresa_cliente = empresa_cliente_id or (
            empresa_cliente.id if empresa_cliente is not None else None
        )
        return UsuarioAutenticadoLeer(
            id=usuario.id,
            tecnico_id=id_tecnico,
            empresa_cliente_id=id_empresa_cliente,
            correo=usuario.correo,
            nombre_completo=usuario.nombre_completo,
            telefono=usuario.telefono,
            numero_documento=usuario.numero_documento,
            ciudad=usuario.ciudad,
            municipio=usuario.municipio,
            direccion=usuario.direccion,
            eps=usuario.eps,
            arl=usuario.arl,
            tiene_vehiculo=usuario.tiene_vehiculo,
            placa_vehiculo=usuario.placa_vehiculo,
            esta_activo=usuario.esta_activo,
            roles=nombres_roles,
            fecha_creacion=usuario.fecha_creacion,
        )
