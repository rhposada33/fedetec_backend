import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "clave-local-para-pruebas-con-longitud-segura"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://fedetec:fedetec@localhost:5432/fedetec"

from app.api.deps import get_db, requerir_admin
from app.api.v1.endpoints import empresas_cliente
from app.core.security import generar_api_key, generar_api_key_hash, verificar_api_key
from app.main import app

client = TestClient(app)
EMPRESA_ID = UUID("11111111-1111-1111-1111-111111111111")
FECHA_CREACION = datetime(2026, 5, 28, tzinfo=UTC)


@pytest.fixture(autouse=True)
def limpiar_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_generar_api_key_hashea_sin_guardar_valor_plano() -> None:
    api_key = generar_api_key()
    api_key_hash = generar_api_key_hash(api_key)

    assert api_key.startswith("fedetec_")
    assert api_key not in api_key_hash
    assert verificar_api_key(api_key, api_key_hash)


def test_requerir_admin_permite_usuario_admin() -> None:
    usuario = SimpleNamespace(
        roles=[SimpleNamespace(rol=SimpleNamespace(nombre="ADMIN"))],
    )

    assert requerir_admin(usuario) is usuario


def test_requerir_admin_rechaza_usuario_no_admin() -> None:
    usuario = SimpleNamespace(
        roles=[SimpleNamespace(rol=SimpleNamespace(nombre="TECNICO"))],
    )

    with pytest.raises(HTTPException) as exc_info:
        requerir_admin(usuario)

    assert exc_info.value.status_code == 403


def test_endpoints_empresas_cliente_exponen_api_key_solo_al_crear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    empresa = SimpleNamespace(
        id=EMPRESA_ID,
        nombre="Cliente Demo",
        identificacion_tributaria="900123456",
        correo_contacto="contacto@example.com",
        telefono_contacto="3001234567",
        esta_activa=True,
        fecha_creacion=FECHA_CREACION,
    )

    class ServicioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def crear(self, empresa_in: object) -> tuple[SimpleNamespace, str]:
            return empresa, "fedetec_api_key_plana"

        async def listar(self) -> list[SimpleNamespace]:
            return [empresa]

        async def obtener(self, empresa_id: UUID) -> SimpleNamespace | None:
            return empresa if empresa_id == EMPRESA_ID else None

        async def actualizar(self, empresa_id: UUID, empresa_in: object) -> SimpleNamespace | None:
            return empresa if empresa_id == EMPRESA_ID else None

    async def obtener_db_fake() -> object:
        yield object()

    app.dependency_overrides[get_db] = obtener_db_fake
    app.dependency_overrides[requerir_admin] = lambda: SimpleNamespace()
    monkeypatch.setattr(empresas_cliente, "EmpresaClienteServicio", ServicioFake)

    payload = {
        "nombre": "Cliente Demo",
        "identificacion_tributaria": "900123456",
        "correo_contacto": "contacto@example.com",
        "telefono_contacto": "3001234567",
        "esta_activa": True,
    }

    crear_response = client.post("/api/v1/empresas-cliente", json=payload)
    listar_response = client.get("/api/v1/empresas-cliente")
    obtener_response = client.get(f"/api/v1/empresas-cliente/{EMPRESA_ID}")
    actualizar_response = client.patch(
        f"/api/v1/empresas-cliente/{EMPRESA_ID}", json={"nombre": "Cliente Demo"}
    )

    assert crear_response.status_code == 201
    assert crear_response.json()["api_key"] == "fedetec_api_key_plana"
    assert "hash_api_key" not in crear_response.json()

    assert listar_response.status_code == 200
    assert "api_key" not in listar_response.json()[0]
    assert "hash_api_key" not in listar_response.json()[0]

    assert obtener_response.status_code == 200
    assert "api_key" not in obtener_response.json()

    assert actualizar_response.status_code == 200
    assert "api_key" not in actualizar_response.json()
