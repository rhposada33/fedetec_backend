import os
from datetime import UTC, datetime
from decimal import Decimal
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
from app.repositorios.propina_servicio import PropinaDuplicadaError
from app.repositorios.servicio import ServicioConUbicacion
from app.schemas.propina_servicio import PropinaServicioCrear
from app.servicios import propina_servicio as propina_modulo
from app.servicios.propina_servicio import PropinaServicioServicio

client = TestClient(app)

EMPRESA_ID = UUID("22222222-2222-2222-2222-222222222222")
OTRA_EMPRESA_ID = UUID("33333333-3333-3333-3333-333333333333")
SERVICIO_ID = UUID("44444444-4444-4444-4444-444444444444")
TECNICO_ID = UUID("55555555-5555-5555-5555-555555555555")
FECHA = datetime(2026, 6, 15, tzinfo=UTC)


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
async def test_crear_propina_vincula_empresa_tecnico_y_recalcula_reporte(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake(estado="PAGO_GENERADO")
    reporte = SimpleNamespace(
        estado="GENERADO",
        valor_base=Decimal("100000.00"),
        valor_propina=Decimal("0"),
        valor=Decimal("100000.00"),
    )

    class SessionFake:
        commits = 0

        async def commit(self) -> None:
            self.__class__.commits += 1

        async def refresh(self, obj: object) -> None:
            obj.id = uuid4()
            obj.fecha_creacion = FECHA

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    class PropinaRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio(self, servicio_id: UUID) -> None:
            return None

        async def crear(self, propina: object) -> object:
            return propina

    class ReporteRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio_id(self, servicio_id: UUID) -> SimpleNamespace:
            return reporte

    monkeypatch.setattr(propina_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(propina_modulo, "PropinaServicioRepositorio", PropinaRepositorioFake)
    monkeypatch.setattr(propina_modulo, "ReportePagoRepositorio", ReporteRepositorioFake)

    propina = await PropinaServicioServicio(SessionFake()).crear(
        SERVICIO_ID, SimpleNamespace(id=EMPRESA_ID), PropinaServicioCrear(valor=Decimal("15000"))
    )

    assert propina is not None
    assert propina.servicio_id == SERVICIO_ID
    assert propina.empresa_cliente_id == EMPRESA_ID
    assert propina.tecnico_id == TECNICO_ID
    assert propina.valor == Decimal("15000")
    assert reporte.valor_propina == Decimal("15000")
    assert reporte.valor == Decimal("115000.00")
    assert SessionFake.commits == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("estado", ["FINALIZADO", "VALIDADO", "PAGO_GENERADO"])
async def test_crear_propina_permite_estados_cerrados(
    monkeypatch: pytest.MonkeyPatch, estado: str
) -> None:
    servicio = crear_servicio_fake(estado=estado)

    class SessionFake:
        async def commit(self) -> None:
            pass

        async def refresh(self, obj: object) -> None:
            obj.id = uuid4()
            obj.fecha_creacion = FECHA

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    class PropinaRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio(self, servicio_id: UUID) -> None:
            return None

        async def crear(self, propina: object) -> object:
            return propina

    class ReporteRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio_id(self, servicio_id: UUID) -> None:
            return None

    monkeypatch.setattr(propina_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(propina_modulo, "PropinaServicioRepositorio", PropinaRepositorioFake)
    monkeypatch.setattr(propina_modulo, "ReportePagoRepositorio", ReporteRepositorioFake)

    propina = await PropinaServicioServicio(SessionFake()).crear(
        SERVICIO_ID, SimpleNamespace(id=EMPRESA_ID), PropinaServicioCrear(valor=Decimal("1"))
    )

    assert propina is not None


@pytest.mark.asyncio
async def test_crear_propina_rechaza_empresa_no_propietaria(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake(empresa_cliente_id=OTRA_EMPRESA_ID)

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    monkeypatch.setattr(propina_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    with pytest.raises(PermissionError):
        await PropinaServicioServicio(SimpleNamespace()).crear(
            SERVICIO_ID, SimpleNamespace(id=EMPRESA_ID), PropinaServicioCrear(valor=Decimal("1"))
        )


@pytest.mark.asyncio
async def test_crear_propina_rechaza_estado_no_cerrado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake(estado="EN_PROCESO")

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    monkeypatch.setattr(propina_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    with pytest.raises(ValueError, match="finalizados"):
        await PropinaServicioServicio(SimpleNamespace()).crear(
            SERVICIO_ID, SimpleNamespace(id=EMPRESA_ID), PropinaServicioCrear(valor=Decimal("1"))
        )


@pytest.mark.asyncio
async def test_crear_propina_rechaza_servicio_sin_tecnico(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake(tecnico_id=None)

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    monkeypatch.setattr(propina_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    with pytest.raises(ValueError, match="tecnico asignado"):
        await PropinaServicioServicio(SimpleNamespace()).crear(
            SERVICIO_ID, SimpleNamespace(id=EMPRESA_ID), PropinaServicioCrear(valor=Decimal("1"))
        )


@pytest.mark.asyncio
async def test_crear_propina_rechaza_duplicado(monkeypatch: pytest.MonkeyPatch) -> None:
    servicio = crear_servicio_fake()

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    class PropinaRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio(self, servicio_id: UUID) -> SimpleNamespace:
            return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(propina_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(propina_modulo, "PropinaServicioRepositorio", PropinaRepositorioFake)

    with pytest.raises(PropinaDuplicadaError):
        await PropinaServicioServicio(SimpleNamespace()).crear(
            SERVICIO_ID, SimpleNamespace(id=EMPRESA_ID), PropinaServicioCrear(valor=Decimal("1"))
        )


@pytest.mark.asyncio
async def test_crear_propina_bloquea_reporte_pagado(monkeypatch: pytest.MonkeyPatch) -> None:
    servicio = crear_servicio_fake()

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    class PropinaRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio(self, servicio_id: UUID) -> None:
            return None

    class ReporteRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio_id(self, servicio_id: UUID) -> SimpleNamespace:
            return SimpleNamespace(estado="PAGADO")

    monkeypatch.setattr(propina_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(propina_modulo, "PropinaServicioRepositorio", PropinaRepositorioFake)
    monkeypatch.setattr(propina_modulo, "ReportePagoRepositorio", ReporteRepositorioFake)

    with pytest.raises(ValueError, match="pagado o anulado"):
        await PropinaServicioServicio(SimpleNamespace()).crear(
            SERVICIO_ID, SimpleNamespace(id=EMPRESA_ID), PropinaServicioCrear(valor=Decimal("1"))
        )


def test_endpoint_crear_propina_valida_monto() -> None:
    async def obtener_db_fake() -> object:
        yield object()

    app.dependency_overrides[get_db] = obtener_db_fake
    app.dependency_overrides[requerir_empresa_cliente] = lambda: SimpleNamespace(id=EMPRESA_ID)

    response = client.post(
        f"/api/v1/servicios/{SERVICIO_ID}/propina",
        headers={"Authorization": "Bearer token-fake"},
        json={"valor": -1},
    )

    assert response.status_code == 422


def test_endpoint_obtener_propina_responde_propina(monkeypatch: pytest.MonkeyPatch) -> None:
    propina = SimpleNamespace(
        id=uuid4(),
        servicio_id=SERVICIO_ID,
        empresa_cliente_id=EMPRESA_ID,
        tecnico_id=TECNICO_ID,
        valor=Decimal("10000.00"),
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
            return propina

    async def obtener_db_fake() -> object:
        yield object()

    app.dependency_overrides[get_db] = obtener_db_fake
    app.dependency_overrides[requerir_empresa_cliente] = lambda: SimpleNamespace(id=EMPRESA_ID)
    monkeypatch.setattr(servicios_endpoint, "PropinaServicioServicio", ServicioFake)

    response = client.get(
        f"/api/v1/servicios/{SERVICIO_ID}/propina",
        headers={"Authorization": "Bearer token-fake"},
    )

    assert response.status_code == 200
    assert response.json()["servicio_id"] == str(SERVICIO_ID)
    assert response.json()["valor"] == "10000.00"
