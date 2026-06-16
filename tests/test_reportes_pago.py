import os
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "clave-local-para-pruebas-con-longitud-segura"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://fedetec:fedetec@localhost:5432/fedetec"

from app.repositorios.reporte_pago import ReportePagoDuplicadoError
from app.schemas.reporte_pago import ReportePagoCrear
from app.servicios import reporte_pago as reporte_modulo
from app.servicios.reporte_pago import ReportePagoServicio

SERVICIO_ID = UUID("33333333-3333-3333-3333-333333333333")
REPORTE_ID = UUID("44444444-4444-4444-4444-444444444444")
TECNICO_ID = UUID("55555555-5555-5555-5555-555555555555")
EMPRESA_ID = UUID("66666666-6666-6666-6666-666666666666")
FECHA = datetime(2026, 5, 28, tzinfo=UTC)


def crear_servicio_fake(estado: str = "FINALIZADO") -> SimpleNamespace:
    return SimpleNamespace(
        id=SERVICIO_ID,
        tecnico_aceptado_id=TECNICO_ID,
        empresa_cliente_id=EMPRESA_ID,
        valor_servicio=Decimal("98000.00"),
        estado=estado,
        fecha_pago_generado=None,
    )


def crear_reporte_fake(valor: Decimal | None = Decimal("125000.00")) -> SimpleNamespace:
    return SimpleNamespace(
        id=REPORTE_ID,
        servicio_id=SERVICIO_ID,
        tecnico_id=TECNICO_ID,
        empresa_cliente_id=EMPRESA_ID,
        valor=valor,
        valor_base=valor or Decimal("0"),
        valor_propina=Decimal("0"),
        estado="GENERADO",
        fecha_generacion=FECHA,
    )


@pytest.mark.asyncio
async def test_crear_reporte_pago_actualiza_estado_servicio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake()

    class SessionFake:
        commits = 0
        refreshes: list[object] = []

        async def commit(self) -> None:
            self.__class__.commits += 1

        async def refresh(self, obj: object) -> None:
            self.__class__.refreshes.append(obj)
            obj.id = REPORTE_ID
            obj.fecha_generacion = FECHA

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return servicio

    class ReporteRepositorioFake:
        reporte_creado = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio_id(self, servicio_id: UUID) -> None:
            return None

        async def crear(self, reporte: object) -> object:
            self.__class__.reporte_creado = reporte
            return reporte

    class PropinaRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio(self, servicio_id: UUID) -> None:
            return None

    monkeypatch.setattr(reporte_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(reporte_modulo, "ReportePagoRepositorio", ReporteRepositorioFake)
    monkeypatch.setattr(reporte_modulo, "PropinaServicioRepositorio", PropinaRepositorioFake)

    reporte = await ReportePagoServicio(SessionFake()).crear(
        SERVICIO_ID, ReportePagoCrear(valor=Decimal("125000.00"))
    )

    assert reporte is not None
    assert reporte.servicio_id == SERVICIO_ID
    assert reporte.tecnico_id == TECNICO_ID
    assert reporte.empresa_cliente_id == EMPRESA_ID
    assert reporte.valor == Decimal("125000.00")
    assert reporte.valor_base == Decimal("125000.00")
    assert reporte.valor_propina == 0
    assert reporte.estado == "GENERADO"
    assert servicio.estado == "PAGO_GENERADO"
    assert servicio.fecha_pago_generado is not None
    assert SessionFake.commits == 1


@pytest.mark.asyncio
async def test_crear_reporte_pago_usa_valor_servicio_por_defecto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake()

    class SessionFake:
        async def commit(self) -> None:
            pass

        async def refresh(self, obj: object) -> None:
            obj.id = REPORTE_ID
            obj.fecha_generacion = FECHA

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return servicio

    class ReporteRepositorioFake:
        reporte_creado = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio_id(self, servicio_id: UUID) -> None:
            return None

        async def crear(self, reporte: object) -> object:
            self.__class__.reporte_creado = reporte
            return reporte

    class PropinaRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio(self, servicio_id: UUID) -> None:
            return None

    monkeypatch.setattr(reporte_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(reporte_modulo, "ReportePagoRepositorio", ReporteRepositorioFake)
    monkeypatch.setattr(reporte_modulo, "PropinaServicioRepositorio", PropinaRepositorioFake)

    reporte = await ReportePagoServicio(SessionFake()).crear(SERVICIO_ID, ReportePagoCrear())

    assert reporte is not None
    assert reporte.valor == Decimal("98000.00")
    assert reporte.valor_base == Decimal("98000.00")
    assert reporte.valor_propina == 0


@pytest.mark.asyncio
async def test_crear_reporte_pago_suma_propina_existente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake()

    class SessionFake:
        async def commit(self) -> None:
            pass

        async def refresh(self, obj: object) -> None:
            obj.id = REPORTE_ID
            obj.fecha_generacion = FECHA

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return servicio

    class ReporteRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio_id(self, servicio_id: UUID) -> None:
            return None

        async def crear(self, reporte: object) -> object:
            return reporte

    class PropinaRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio(self, servicio_id: UUID) -> SimpleNamespace:
            return SimpleNamespace(valor=Decimal("12000.00"))

    monkeypatch.setattr(reporte_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(reporte_modulo, "ReportePagoRepositorio", ReporteRepositorioFake)
    monkeypatch.setattr(reporte_modulo, "PropinaServicioRepositorio", PropinaRepositorioFake)

    reporte = await ReportePagoServicio(SessionFake()).crear(SERVICIO_ID, ReportePagoCrear())

    assert reporte is not None
    assert reporte.valor_base == Decimal("98000.00")
    assert reporte.valor_propina == Decimal("12000.00")
    assert reporte.valor == Decimal("110000.00")


@pytest.mark.asyncio
async def test_crear_reporte_pago_previene_duplicados(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return crear_servicio_fake()

    class ReporteRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_servicio_id(self, servicio_id: UUID) -> SimpleNamespace:
            return crear_reporte_fake()

    monkeypatch.setattr(reporte_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(reporte_modulo, "ReportePagoRepositorio", ReporteRepositorioFake)

    with pytest.raises(ReportePagoDuplicadoError, match="Ya existe"):
        await ReportePagoServicio(SimpleNamespace()).crear(SERVICIO_ID, ReportePagoCrear())


@pytest.mark.asyncio
async def test_crear_reporte_pago_valida_estado_servicio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return crear_servicio_fake(estado="EN_PROCESO")

    monkeypatch.setattr(reporte_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    with pytest.raises(ValueError, match="FINALIZADO o VALIDADO"):
        await ReportePagoServicio(SimpleNamespace()).crear(SERVICIO_ID, ReportePagoCrear())


@pytest.mark.asyncio
async def test_reportes_pago_listar_y_obtener_retornan_datos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reporte = crear_reporte_fake()

    class ReporteRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def listar(self) -> list[SimpleNamespace]:
            return [reporte]

        async def obtener_por_id(self, reporte_id: UUID) -> SimpleNamespace:
            return reporte

    monkeypatch.setattr(reporte_modulo, "ReportePagoRepositorio", ReporteRepositorioFake)

    servicio = ReportePagoServicio(SimpleNamespace())

    assert await servicio.listar() == [reporte]
    assert await servicio.obtener(REPORTE_ID) is reporte
