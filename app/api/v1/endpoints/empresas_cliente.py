from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminDep, SesionDep
from app.schemas.empresa_cliente import (
    EmpresaClienteActualizar,
    EmpresaClienteCreada,
    EmpresaClienteCrear,
    EmpresaClienteLeer,
)
from app.servicios.empresa_cliente import EmpresaClienteServicio

router = APIRouter()


@router.post("", response_model=EmpresaClienteCreada, status_code=status.HTTP_201_CREATED)
async def crear_empresa_cliente(
    empresa_in: EmpresaClienteCrear, session: SesionDep, _admin: AdminDep
) -> EmpresaClienteCreada:
    empresa, api_key = await EmpresaClienteServicio(session).crear(empresa_in)
    empresa_leer = EmpresaClienteLeer.model_validate(empresa, from_attributes=True)
    return EmpresaClienteCreada(**empresa_leer.model_dump(), api_key=api_key)


@router.get("", response_model=list[EmpresaClienteLeer])
async def listar_empresas_cliente(
    session: SesionDep, _admin: AdminDep
) -> list[EmpresaClienteLeer]:
    return await EmpresaClienteServicio(session).listar()


@router.get("/{empresa_id}", response_model=EmpresaClienteLeer)
async def obtener_empresa_cliente(
    empresa_id: UUID, session: SesionDep, _admin: AdminDep
) -> EmpresaClienteLeer:
    empresa = await EmpresaClienteServicio(session).obtener(empresa_id)
    if empresa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa cliente no encontrada",
        )
    return empresa


@router.patch("/{empresa_id}", response_model=EmpresaClienteLeer)
async def actualizar_empresa_cliente(
    empresa_id: UUID,
    empresa_in: EmpresaClienteActualizar,
    session: SesionDep,
    _admin: AdminDep,
) -> EmpresaClienteLeer:
    empresa = await EmpresaClienteServicio(session).actualizar(empresa_id, empresa_in)
    if empresa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa cliente no encontrada",
        )
    return empresa
