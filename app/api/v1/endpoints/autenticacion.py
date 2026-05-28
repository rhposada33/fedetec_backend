from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import SesionDep, UsuarioActualDep
from app.schemas.autenticacion import TecnicoRegistrar, UsuarioAutenticadoLeer
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


@router.post(
    "/registro/tecnico",
    response_model=UsuarioAutenticadoLeer,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_tecnico(
    tecnico_in: TecnicoRegistrar, session: SesionDep
) -> UsuarioAutenticadoLeer:
    servicio = AutenticacionServicio(session)
    try:
        return await servicio.registrar_tecnico(tecnico_in)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/login", response_model=Token)
async def iniciar_sesion(
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


@router.post("/token", response_model=Token, include_in_schema=False)
async def crear_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SesionDep
) -> Token:
    return await iniciar_sesion(form_data, session)


@router.get("/yo", response_model=UsuarioAutenticadoLeer)
async def leer_usuario_autenticado(
    usuario_actual: UsuarioActualDep, session: SesionDep
) -> UsuarioAutenticadoLeer:
    usuario = await AutenticacionServicio(session).obtener_usuario_autenticado(usuario_actual.id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudieron validar las credenciales",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario
