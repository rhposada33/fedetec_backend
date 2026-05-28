from fastapi import APIRouter, status

from app.api.deps import SesionDep, UsuarioActualDep
from app.schemas.sede import SedeCrear, SedeLeer
from app.servicios.sede import SedeServicio

router = APIRouter()


@router.get("", response_model=list[SedeLeer])
async def listar_sedes(session: SesionDep) -> list[SedeLeer]:
    return await SedeServicio(session).listar()


@router.post("", response_model=SedeLeer, status_code=status.HTTP_201_CREATED)
async def crear_sede(
    sede_in: SedeCrear, session: SesionDep, _usuario_actual: UsuarioActualDep
) -> SedeLeer:
    return await SedeServicio(session).crear(sede_in)

