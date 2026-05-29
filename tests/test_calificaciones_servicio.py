import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "clave-local-para-pruebas-con-longitud-segura"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://fedetec:fedetec@localhost:5432/fedetec"

from app.api.deps import get_db, requerir_empresa_cliente
from app.api.v1.endpoints import servicios as servicios_endpoint
from app.main import app
from app.repositorios.calificacion_servicio import CalificacionDuplicadaError
from app.repositorios.servicio import ServicioConUbicacion
from app.schemas.calificacion_servicio import CalificacionServicioCrear
from app.servicios import calificacion_servicio as calificacion_modulo
from app.servicios.calificacion_servicio import CalificacionServicioServicio

client = TestClient(app)

EMPRESA_ID = UUID("22222222-2222-2222-2222-222222222222")
OTRA_EMPRESA_ID = UUID("33333333-3333-3333-3333-333333333333")
SERVICIO_ID = UUID("44444444-4444-4444-4444-444444444444")
TECNICO_ID = UUID("55555555-5555-5555-5555-555555555555")
FECHA = datetime(2026, 5, 29, tzinfo=UTC)


@pytest.fixture(autouse=True)
def limpiar_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def crear_servicio_fake(
    estado: str = "FINALIZADO",
    empresa_cliente_id: UUID = EMPRESA_ID,
    tecnico_id: UUID | None = TECNICO_ID,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=SERVICIO_ID,
        empresa_cliente_id=empresa_cliente_id,
        estado=estado,
        tecnico_aceptado_id=tecnico_id,
    )


@pytest.mark.asyncio
async def test_crear_calificacion_vincula_empresa_y_tecnico(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake()

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion | None:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    class CalificacionRepositorioFake:
        creada: object | None = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio(self, servicio_id: UUID) -> None:
            return None

        async def crear(self, calificacion: object) -> object:
            calificacion.id = uuid4()
            calificacion.fecha_calificacion = FECHA
            calificacion.fecha_creacion = FECHA
            self.__class__.creada = calificacion
            return calificacion

    monkeypatch.setattr(calificacion_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(
        calificacion_modulo, "CalificacionServicioRepositorio", CalificacionRepositorioFake
    )

    empresa = SimpleNamespace(id=EMPRESA_ID)
    calificacion = await CalificacionServicioServicio(object()).crear(
        SERVICIO_ID,
        empresa,
        CalificacionServicioCrear(puntuacion=5, comentario="Excelente servicio"),
    )

    assert calificacion is not None
    assert calificacion.servicio_id == SERVICIO_ID
    assert calificacion.empresa_cliente_id == EMPRESA_ID
    assert calificacion.tecnico_id == TECNICO_ID
    assert calificacion.puntuacion == 5


@pytest.mark.asyncio
async def test_crear_calificacion_rechaza_empresa_no_propietaria(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake(empresa_cliente_id=OTRA_EMPRESA_ID)

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion | None:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    monkeypatch.setattr(calificacion_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    with pytest.raises(PermissionError):
        await CalificacionServicioServicio(object()).crear(
            SERVICIO_ID,
            SimpleNamespace(id=EMPRESA_ID),
            CalificacionServicioCrear(puntuacion=4),
        )


@pytest.mark.asyncio
async def test_crear_calificacion_rechaza_estado_no_calificable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake(estado="CREADO")

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion | None:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    monkeypatch.setattr(calificacion_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    with pytest.raises(ValueError):
        await CalificacionServicioServicio(object()).crear(
            SERVICIO_ID,
            SimpleNamespace(id=EMPRESA_ID),
            CalificacionServicioCrear(puntuacion=4),
        )


@pytest.mark.asyncio
async def test_crear_calificacion_rechaza_duplicado(monkeypatch: pytest.MonkeyPatch) -> None:
    servicio = crear_servicio_fake()

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion | None:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    class CalificacionRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio(self, servicio_id: UUID) -> SimpleNamespace:
            return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(calificacion_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(
        calificacion_modulo, "CalificacionServicioRepositorio", CalificacionRepositorioFake
    )

    with pytest.raises(CalificacionDuplicadaError):
        await CalificacionServicioServicio(object()).crear(
            SERVICIO_ID,
            SimpleNamespace(id=EMPRESA_ID),
            CalificacionServicioCrear(puntuacion=4),
        )


def test_endpoint_crear_calificacion_valida_puntuacion() -> None:
    async def obtener_db_fake() -> object:
        yield object()

    app.dependency_overrides[get_db] = obtener_db_fake
    app.dependency_overrides[requerir_empresa_cliente] = lambda: SimpleNamespace(id=EMPRESA_ID)

    response = client.post(
        f"/api/v1/servicios/{SERVICIO_ID}/calificaciones",
        headers={"Authorization": "Bearer token-fake"},
        json={"puntuacion": 6, "comentario": "Fuera de escala"},
    )

    assert response.status_code == 422


def test_endpoint_crear_calificacion_responde_calificacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calificacion = SimpleNamespace(
        id=uuid4(),
        servicio_id=SERVICIO_ID,
        empresa_cliente_id=EMPRESA_ID,
        tecnico_id=TECNICO_ID,
        puntuacion=5,
        comentario="Muy buen servicio",
        fecha_calificacion=FECHA,
        fecha_creacion=FECHA,
    )

    class ServicioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def crear(
            self,
            servicio_id: UUID,
            empresa_cliente: SimpleNamespace,
            calificacion_in: object,
        ) -> SimpleNamespace:
            return calificacion

    async def obtener_db_fake() -> object:
        yield object()

    app.dependency_overrides[get_db] = obtener_db_fake
    app.dependency_overrides[requerir_empresa_cliente] = lambda: SimpleNamespace(id=EMPRESA_ID)
    monkeypatch.setattr(servicios_endpoint, "CalificacionServicioServicio", ServicioFake)

    response = client.post(
        f"/api/v1/servicios/{SERVICIO_ID}/calificaciones",
        headers={"Authorization": "Bearer token-fake"},
        json={"puntuacion": 5, "comentario": "Muy buen servicio"},
    )

    assert response.status_code == 201
    assert response.json()["servicio_id"] == str(SERVICIO_ID)
    assert response.json()["tecnico_id"] == str(TECNICO_ID)
    assert response.json()["puntuacion"] == 5


def test_endpoint_obtener_calificacion_responde_calificacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calificacion = SimpleNamespace(
        id=uuid4(),
        servicio_id=SERVICIO_ID,
        empresa_cliente_id=EMPRESA_ID,
        tecnico_id=TECNICO_ID,
        puntuacion=4,
        comentario="Buen servicio",
        fecha_calificacion=FECHA,
        fecha_creacion=FECHA,
    )

    class ServicioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener(
            self,
            servicio_id: UUID,
            empresa_cliente: SimpleNamespace,
        ) -> SimpleNamespace:
            return calificacion

    async def obtener_db_fake() -> object:
        yield object()

    app.dependency_overrides[get_db] = obtener_db_fake
    app.dependency_overrides[requerir_empresa_cliente] = lambda: SimpleNamespace(id=EMPRESA_ID)
    monkeypatch.setattr(servicios_endpoint, "CalificacionServicioServicio", ServicioFake)

    response = client.get(
        f"/api/v1/servicios/{SERVICIO_ID}/calificaciones",
        headers={"Authorization": "Bearer token-fake"},
    )

    assert response.status_code == 200
    assert response.json()["servicio_id"] == str(SERVICIO_ID)
    assert response.json()["puntuacion"] == 4
