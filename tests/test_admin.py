import os
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "clave-local-para-pruebas-con-longitud-segura"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://fedetec:fedetec@localhost:5432/fedetec"

from app.main import app
from app.repositorios.servicio import ServicioRepositorio
from app.schemas.admin import ConfiguracionActualizar, ConfiguracionAprobacionEvidenciasLeer
from app.schemas.tipo_servicio import TipoServicioActualizar, TipoServicioCrear
from app.servicios import admin as admin_modulo
from app.servicios.admin import AdminServicio

client = TestClient(app)
EMPRESA_ID = UUID("22222222-2222-2222-2222-222222222222")
TECNICO_ID = UUID("44444444-4444-4444-4444-444444444444")
FECHA_DESDE = datetime(2026, 5, 1, tzinfo=UTC)
FECHA_HASTA = datetime(2026, 5, 28, tzinfo=UTC)


@pytest.fixture(autouse=True)
def limpiar_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_metricas_por_estado(monkeypatch: pytest.MonkeyPatch) -> None:
    class ServicioRepositorioFake:
        filtros = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def contar_por_estado(self, *args: object) -> dict[str, int]:
            self.__class__.filtros = args
            return {"ACEPTADO": 2, "FINALIZADO": 3}

    monkeypatch.setattr(admin_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    respuesta = await AdminServicio(object()).dashboard(
        "ACEPTADO", EMPRESA_ID, TECNICO_ID, FECHA_DESDE, FECHA_HASTA
    )

    assert respuesta.total_servicios == 5
    assert [(item.estado, item.total) for item in respuesta.servicios_por_estado] == [
        ("ACEPTADO", 2),
        ("FINALIZADO", 3),
    ]
    assert ServicioRepositorioFake.filtros == (
        "ACEPTADO",
        EMPRESA_ID,
        TECNICO_ID,
        FECHA_DESDE,
        FECHA_HASTA,
    )


@pytest.mark.asyncio
async def test_filtros_admin_servicios_se_aplican_en_sql() -> None:
    class ResultadoFake:
        def all(self) -> list[object]:
            return []

    class SessionFake:
        statement = None

        async def execute(self, statement: object) -> ResultadoFake:
            self.__class__.statement = statement
            return ResultadoFake()

    await ServicioRepositorio(SessionFake()).listar_admin(
        estado="FINALIZADO",
        empresa_cliente_id=EMPRESA_ID,
        tecnico_id=TECNICO_ID,
        fecha_desde=FECHA_DESDE,
        fecha_hasta=FECHA_HASTA,
    )

    sql = str(
        SessionFake.statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}
        )
    )

    assert "servicios.estado = " in sql
    assert "servicios.empresa_cliente_id = " in sql
    assert "servicios.tecnico_aceptado_id = " in sql
    assert "servicios.fecha_creacion >= " in sql
    assert "servicios.fecha_creacion <= " in sql


@pytest.mark.asyncio
async def test_actualizar_configuracion_persiste_modo_aprobacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ConfiguracionRepositorioFake:
        valor_guardado = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def guardar_valor(self, clave: str, valor: dict) -> SimpleNamespace:
            self.__class__.valor_guardado = (clave, valor)
            return SimpleNamespace(valor=valor, fecha_actualizacion=FECHA_HASTA)

    monkeypatch.setattr(admin_modulo, "ConfiguracionAppRepositorio", ConfiguracionRepositorioFake)

    respuesta = await AdminServicio(object()).actualizar_configuracion(
        ConfiguracionActualizar(
            aprobacion_evidencias=ConfiguracionAprobacionEvidenciasLeer(
                modo="AUTO", roles_permitidos=["ADMIN"]
            )
        )
    )

    assert ConfiguracionRepositorioFake.valor_guardado == (
        "aprobacion_evidencias",
        {"modo": "AUTO", "roles_permitidos": ["ADMIN"]},
    )
    assert respuesta.aprobacion_evidencias.modo == "AUTO"
    assert respuesta.fecha_actualizacion == FECHA_HASTA


@pytest.mark.asyncio
async def test_admin_tipos_servicio_crud_logico(monkeypatch: pytest.MonkeyPatch) -> None:
    tipo = SimpleNamespace(
        id=10,
        nombre="Instalacion",
        valor=Decimal("150000.00"),
        esta_activo=True,
        fecha_creacion=FECHA_HASTA,
        fecha_actualizacion=FECHA_HASTA,
    )

    class TipoServicioRepositorioFake:
        solo_activos = None
        creado = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def listar(self, solo_activos: bool = False) -> list[SimpleNamespace]:
            self.__class__.solo_activos = solo_activos
            return [tipo]

        async def obtener_por_id(self, tipo_servicio_id: int) -> SimpleNamespace:
            return tipo

        async def crear(self, tipo_servicio: object) -> SimpleNamespace:
            self.__class__.creado = tipo_servicio
            tipo_servicio.id = tipo.id
            tipo_servicio.fecha_creacion = FECHA_HASTA
            tipo_servicio.fecha_actualizacion = FECHA_HASTA
            return tipo_servicio

        async def guardar(self, tipo_servicio: object) -> SimpleNamespace:
            tipo_servicio.fecha_actualizacion = FECHA_HASTA
            return tipo_servicio

    monkeypatch.setattr(admin_modulo, "TipoServicioRepositorio", TipoServicioRepositorioFake)
    servicio = AdminServicio(object())

    listado = await servicio.listar_tipos_servicio(solo_activos=True)
    creado = await servicio.crear_tipo_servicio(
        TipoServicioCrear(nombre="Instalacion", valor=Decimal("150000.00"))
    )
    actualizado = await servicio.actualizar_tipo_servicio(
        tipo.id, TipoServicioActualizar(nombre="Instalacion premium", valor=Decimal("180000.00"))
    )
    desactivado = await servicio.desactivar_tipo_servicio(tipo.id)

    assert TipoServicioRepositorioFake.solo_activos is True
    assert listado[0].nombre == "Instalacion"
    assert creado.valor == Decimal("150000.00")
    assert actualizado is not None
    assert actualizado.nombre == "Instalacion premium"
    assert desactivado is not None
    assert desactivado.esta_activo is False


def test_admin_dashboard_sin_admin_es_denegado() -> None:
    response = client.get("/api/v1/admin/dashboard")

    assert response.status_code == 401
