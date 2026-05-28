from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import SesionDep
from app.schemas.token import Token
from app.schemas.usuario import UsuarioCrear, UsuarioLeer
from app.servicios.autenticacion import AutenticacionServicio

router = APIRouter()


@router.post("/registro", response_model=UsuarioLeer, status_code=status.HTTP_201_CREATED)
async def registrar_usuario(usuario_in: UsuarioCrear, session: SesionDep) -> UsuarioLeer:
    servicio = AutenticacionServicio(session)
    try:
        return await servicio.registrar_usuario(usuario_in)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/token", response_model=Token)
async def crear_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SesionDep
) -> Token:
    servicio = AutenticacionServicio(session)
    token = await servicio.autenticar(correo=form_data.username, password=form_data.password)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o password incorrecto",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=token)
