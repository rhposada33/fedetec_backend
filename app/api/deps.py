from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decodificar_token
from app.modelos.usuario import Usuario
from app.repositorios.usuario import UsuarioRepositorio

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/autenticacion/token")
SesionDep = Annotated[AsyncSession, Depends(get_db)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


async def obtener_usuario_actual(session: SesionDep, token: TokenDep) -> Usuario:
    credenciales_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decodificar_token(token)
        usuario_id = UUID(str(payload.get("sub")))
    except (TypeError, ValueError):
        raise credenciales_error from None

    usuario = await UsuarioRepositorio(session).obtener_por_id(usuario_id)
    if usuario is None or not usuario.esta_activo:
        raise credenciales_error
    return usuario


UsuarioActualDep = Annotated[Usuario, Depends(obtener_usuario_actual)]
