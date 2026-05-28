import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "clave-local-para-pruebas-con-longitud-segura"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://fedetec:fedetec@localhost:5432/fedetec"

from app.api import deps
from app.api.deps import get_db, obtener_empresa_cliente_por_api_key
from app.core.security import generar_api_key_hash
from app.main import app
from app.repositorios.servicio import ServicioConUbicacion
from app.servicios import servicio as servicio_modulo
from app.servicios.servicio import ServicioServicio

client = TestClient(app)
EMPRESA_ID = UUID("22222222-2222-2222-2222-222222222222")
SERVICIO_ID = UUID("33333333-3333-3333-3333-333333333333")
FECHA = datetime(2026, 5, 28, tzinfo=UTC)


@pytest.fixture(autouse=True)
def limpiar_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_key_authentica_empresa_activa(monkeypatch: pytest.MonkeyPatch) -> None:
    api_key = "fedetec_api_key_valida"
    empresa = SimpleNamespace(
        id=EMPRESA_ID,
        esta_activa=True,
        hash_api_key=generar_api_key_hash(api_key),
    )

    class RepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def listar_activas_con_api_key(self) -> list[SimpleNamespace]:
            return [empresa]

    monkeypatch.setattr(deps, "EmpresaClienteRepositorio", RepositorioFake)

    autenticada = await obtener_empresa_cliente_por_api_key(object(), x_api_key=api_key)

    assert autenticada is empresa


def test_post_servicio_rechaza_tipo_invalido() -> None:
    async def obtener_db_fake() -> object:
        yield object()

    app.dependency_overrides[get_db] = obtener_db_fake
    app.dependency_overrides[deps.obtener_empresa_cliente_por_api_key] = lambda: SimpleNamespace(
        id=EMPRESA_ID
    )

    response = client.post(
        "/api/v1/servicios",
        headers={"X-API-Key": "fedetec_api_key_valida", "Idempotency-Key": "req-1"},
        json={
            "tipo_servicio": 99,
            "latitud": 4.711,
            "longitud": -74.0721,
            "fecha_programada": FECHA.isoformat(),
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_crear_servicio_es_idempotente_y_guarda_ubicacion_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RepositorioFake:
        servicios_por_clave: dict[str, ServicioConUbicacion] = {}
        ubicacion_guardada: str | None = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def crear_idempotente(
            self, servicio: object, clave_idempotencia: str
        ) -> ServicioConUbicacion:
            existente = self.servicios_por_clave.get(clave_idempotencia)
            if existente is not None:
                return existente

            servicio.id = uuid4()
            servicio.fecha_creacion = FECHA
            servicio.fecha_actualizacion = FECHA
            self.ubicacion_guardada = servicio.ubicacion.desc
            self.__class__.ubicacion_guardada = servicio.ubicacion.desc
            creado = ServicioConUbicacion(servicio, 4.711, -74.0721)
            self.servicios_por_clave[clave_idempotencia] = creado
            return creado

    monkeypatch.setattr(servicio_modulo, "ServicioRepositorio", RepositorioFake)

    empresa = SimpleNamespace(id=EMPRESA_ID)
    servicio_in = servicio_modulo.ServicioCrear(
        tipo_servicio=1,
        placa_vehiculo="ABC123",
        latitud=4.711,
        longitud=-74.0721,
        direccion="Calle 1",
        fecha_programada=FECHA,
    )
    servicio = ServicioServicio(object())

    creado = await servicio.crear(servicio_in, empresa, "req-duplicada")
    duplicado = await servicio.crear(servicio_in, empresa, "req-duplicada")

    assert duplicado.id == creado.id
    assert creado.estado == "CREADO"
    assert RepositorioFake.ubicacion_guardada == "POINT(-74.0721 4.711)"
    assert creado.latitud == 4.711
    assert creado.longitud == -74.0721


def test_post_servicio_requiere_idempotency_key() -> None:
    async def obtener_db_fake() -> object:
        yield object()

    app.dependency_overrides[get_db] = obtener_db_fake
    app.dependency_overrides[deps.obtener_empresa_cliente_por_api_key] = lambda: SimpleNamespace(
        id=EMPRESA_ID
    )

    response = client.post(
        "/api/v1/servicios",
        headers={"X-API-Key": "fedetec_api_key_valida"},
        json={
            "tipo_servicio": 1,
            "latitud": 4.711,
            "longitud": -74.0721,
            "fecha_programada": FECHA.isoformat(),
        },
    )

    assert response.status_code == 400
