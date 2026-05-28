from fastapi import APIRouter

from app.api.deps import UsuarioActualDep
from app.schemas.usuario import UsuarioLeer

router = APIRouter()


@router.get("/me", response_model=UsuarioLeer)
async def leer_usuario_actual(usuario_actual: UsuarioActualDep) -> UsuarioLeer:
    return usuario_actual

