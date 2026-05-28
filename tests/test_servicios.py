import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "clave-local-para-pruebas-con-longitud-segura"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://fedetec:fedetec@localhost:5432/fedetec"

from app.api import deps
from app.api.deps import get_db, obtener_empresa_cliente_por_api_key
from app.core.security import generar_api_key_hash
from app.main import app
from app.repositorios.notificacion_servicio import NotificacionServicioRepositorio
from app.repositorios.rechazo_servicio import RechazoServicioRepositorio
from app.repositorios.servicio import ServicioConUbicacion, ServicioRepositorio
from app.repositorios.tecnico import TecnicoConUbicacion
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


def crear_servicio_fake(estado: str = "CREADO") -> SimpleNamespace:
    return SimpleNamespace(
        id=SERVICIO_ID,
        empresa_cliente_id=EMPRESA_ID,
        tipo_servicio=1,
        placa_vehiculo="ABC123",
        direccion="Calle 1",
        fecha_programada=FECHA,
        estado=estado,
        clave_idempotencia="req-publicar",
        fecha_creacion=FECHA,
        fecha_actualizacion=FECHA,
        tecnico_aceptado_id=None,
        fecha_aceptacion=None,
        fecha_inicio=None,
        fecha_finalizacion=None,
    )


def crear_tecnico_fake() -> SimpleNamespace:
    return SimpleNamespace(id=UUID("44444444-4444-4444-4444-444444444444"))


@pytest.mark.asyncio
async def test_publicar_servicio_selecciona_cercanos_notifica_y_cambia_estado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake()
    tecnico_1 = SimpleNamespace(id=UUID("44444444-4444-4444-4444-444444444444"))
    tecnico_2 = SimpleNamespace(id=UUID("55555555-5555-5555-5555-555555555555"))

    class ServicioRepositorioFake:
        estado_guardado: str | None = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion | None:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

        async def guardar(self, servicio_actualizado: SimpleNamespace) -> SimpleNamespace:
            self.__class__.estado_guardado = servicio_actualizado.estado
            servicio_actualizado.fecha_actualizacion = FECHA
            return servicio_actualizado

    class TecnicoRepositorioFake:
        busqueda: tuple[float, float, int] | None = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def buscar_cercanos(
            self, latitud: float, longitud: float, radio_metros: int
        ) -> list[TecnicoConUbicacion]:
            self.__class__.busqueda = (latitud, longitud, radio_metros)
            return [
                TecnicoConUbicacion(tecnico_1, 4.712, -74.073, 120.0),
                TecnicoConUbicacion(tecnico_2, 4.713, -74.074, 180.0),
            ]

    class NotificacionRepositorioFake:
        tecnico_ids_notificados: list[UUID] = []

        def __init__(self, session: object) -> None:
            self.session = session

        async def crear_para_tecnicos_una_vez(
            self, servicio_id: UUID, tecnico_ids: list[UUID]
        ) -> int:
            self.__class__.tecnico_ids_notificados = tecnico_ids
            return len(tecnico_ids)

    monkeypatch.setattr(servicio_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(servicio_modulo, "TecnicoRepositorio", TecnicoRepositorioFake)
    monkeypatch.setattr(
        servicio_modulo, "NotificacionServicioRepositorio", NotificacionRepositorioFake
    )

    respuesta = await ServicioServicio(object()).publicar(SERVICIO_ID, radio_metros=5000)

    assert respuesta is not None
    assert TecnicoRepositorioFake.busqueda == (4.711, -74.0721, 5000)
    assert NotificacionRepositorioFake.tecnico_ids_notificados == [tecnico_1.id, tecnico_2.id]
    assert ServicioRepositorioFake.estado_guardado == "DISPONIBLE"
    assert respuesta.estado == "DISPONIBLE"
    assert respuesta.notificaciones_creadas == 2
    assert respuesta.tecnicos_cercanos == 2


@pytest.mark.asyncio
async def test_publicar_servicio_rechaza_estado_distinto_a_creado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake(estado="DISPONIBLE")

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion | None:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    monkeypatch.setattr(servicio_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    with pytest.raises(ValueError, match="estado CREADO"):
        await ServicioServicio(object()).publicar(SERVICIO_ID)


def test_notificaciones_servicio_usa_on_conflict_para_evitar_duplicados() -> None:
    class ResultadoFake:
        rowcount = 0

    class SessionFake:
        statement = None

        async def execute(self, statement: object) -> ResultadoFake:
            self.__class__.statement = statement
            return ResultadoFake()

    tecnico_id = UUID("44444444-4444-4444-4444-444444444444")

    async def ejecutar() -> None:
        await NotificacionServicioRepositorio(SessionFake()).crear_para_tecnicos_una_vez(
            SERVICIO_ID, [tecnico_id]
        )

    import asyncio

    asyncio.run(ejecutar())

    sql = str(SessionFake.statement)
    assert "ON CONFLICT ON CONSTRAINT uq_notificaciones_servicio_servicio_id_tecnico_id" in sql


def test_publicar_servicio_sin_admin_es_denegado() -> None:
    response = client.post(f"/api/v1/servicios/{SERVICIO_ID}/publicar")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_aceptar_servicio_usa_bloqueo_y_cambia_estado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake(estado="DISPONIBLE")
    tecnico = crear_tecnico_fake()

    class SessionFake:
        commits = 0

        async def commit(self) -> None:
            self.__class__.commits += 1

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return servicio

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    class NotificacionRepositorioFake:
        estado_notificacion: str | None = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def actualizar_estado_para_tecnico(
            self, servicio_id: UUID, tecnico_id: UUID, estado: str
        ) -> int:
            self.__class__.estado_notificacion = estado
            return 1

    monkeypatch.setattr(servicio_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(
        servicio_modulo, "NotificacionServicioRepositorio", NotificacionRepositorioFake
    )

    respuesta = await ServicioServicio(SessionFake()).aceptar(SERVICIO_ID, tecnico)

    assert respuesta is not None
    assert respuesta.estado == "ACEPTADO"
    assert servicio.tecnico_aceptado_id == tecnico.id
    assert servicio.fecha_aceptacion is not None
    assert NotificacionRepositorioFake.estado_notificacion == "ACEPTADA"
    assert SessionFake.commits == 1


@pytest.mark.asyncio
async def test_aceptar_servicio_first_technician_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake(estado="ACEPTADO")
    servicio.tecnico_aceptado_id = UUID("55555555-5555-5555-5555-555555555555")

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return servicio

    monkeypatch.setattr(servicio_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    with pytest.raises(ValueError, match="ya no esta disponible"):
        await ServicioServicio(SimpleNamespace()).aceptar(SERVICIO_ID, crear_tecnico_fake())


@pytest.mark.asyncio
async def test_obtener_servicio_para_actualizar_usa_for_update() -> None:
    class SessionFake:
        statement = None

        async def scalar(self, statement: object) -> None:
            self.__class__.statement = statement
            return None

    await ServicioRepositorio(SessionFake()).obtener_por_id_para_actualizar(SERVICIO_ID)

    sql = str(
        SessionFake.statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}
        )
    )
    assert "FOR UPDATE" in sql


@pytest.mark.asyncio
async def test_rechazar_servicio_es_unico_y_oculta_notificacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake(estado="DISPONIBLE")
    tecnico = crear_tecnico_fake()

    class SessionFake:
        commits = 0

        async def commit(self) -> None:
            self.__class__.commits += 1

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    class RechazoRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def crear_una_vez(
            self, servicio_id: UUID, tecnico_id: UUID, motivo: str | None = None
        ) -> bool:
            return True

    class NotificacionRepositorioFake:
        estado_notificacion: str | None = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def actualizar_estado_para_tecnico(
            self, servicio_id: UUID, tecnico_id: UUID, estado: str
        ) -> int:
            self.__class__.estado_notificacion = estado
            return 1

    monkeypatch.setattr(servicio_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(servicio_modulo, "RechazoServicioRepositorio", RechazoRepositorioFake)
    monkeypatch.setattr(
        servicio_modulo, "NotificacionServicioRepositorio", NotificacionRepositorioFake
    )

    respuesta = await ServicioServicio(SessionFake()).rechazar(
        SERVICIO_ID, tecnico, servicio_modulo.ServicioRechazar(motivo="No disponible")
    )

    assert respuesta is not None
    assert respuesta.rechazo_creado is True
    assert NotificacionRepositorioFake.estado_notificacion == "RECHAZADA"
    assert SessionFake.commits == 1


def test_rechazo_servicio_usa_on_conflict_para_evitar_duplicados() -> None:
    class ResultadoFake:
        rowcount = 0

    class SessionFake:
        statement = None

        async def execute(self, statement: object) -> ResultadoFake:
            self.__class__.statement = statement
            return ResultadoFake()

    async def ejecutar() -> None:
        await RechazoServicioRepositorio(SessionFake()).crear_una_vez(
            SERVICIO_ID, crear_tecnico_fake().id, "No disponible"
        )

    import asyncio

    asyncio.run(ejecutar())

    sql = str(SessionFake.statement)
    assert "ON CONFLICT ON CONSTRAINT uq_rechazos_servicio_servicio_id_tecnico_id" in sql


@pytest.mark.asyncio
async def test_reprogramar_crea_propuesta_pendiente_y_cambia_estado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake(estado="ACEPTADO")
    tecnico = crear_tecnico_fake()

    class SessionFake:
        commits = 0

        async def commit(self) -> None:
            self.__class__.commits += 1

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return servicio

    class ReprogramacionRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def crear(self, reprogramacion: object) -> object:
            reprogramacion.id = UUID("66666666-6666-6666-6666-666666666666")
            reprogramacion.fecha_creacion = FECHA
            return reprogramacion

    monkeypatch.setattr(servicio_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(
        servicio_modulo, "ReprogramacionServicioRepositorio", ReprogramacionRepositorioFake
    )

    respuesta = await ServicioServicio(SessionFake()).reprogramar(
        SERVICIO_ID,
        tecnico,
        servicio_modulo.ServicioReprogramar(fecha_propuesta=FECHA, motivo="Trafico"),
    )

    assert respuesta is not None
    assert respuesta.estado == "PENDIENTE"
    assert respuesta.tecnico_id == tecnico.id
    assert servicio.estado == "REPROGRAMACION_SOLICITADA"
    assert SessionFake.commits == 1


@pytest.mark.asyncio
async def test_iniciar_servicio_valida_asignado_y_guarda_fecha_inicio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico_fake()
    servicio = crear_servicio_fake(estado="ACEPTADO")
    servicio.tecnico_aceptado_id = tecnico.id

    class SessionFake:
        commits = 0

        async def commit(self) -> None:
            self.__class__.commits += 1

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return servicio

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    monkeypatch.setattr(servicio_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    respuesta = await ServicioServicio(SessionFake()).iniciar(SERVICIO_ID, tecnico)

    assert respuesta is not None
    assert respuesta.estado == "EN_PROCESO"
    assert respuesta.fecha_inicio is not None
    assert servicio.fecha_inicio is not None
    assert SessionFake.commits == 1


@pytest.mark.asyncio
async def test_iniciar_servicio_rechaza_tecnico_no_asignado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio = crear_servicio_fake(estado="ACEPTADO")
    servicio.tecnico_aceptado_id = UUID("77777777-7777-7777-7777-777777777777")

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return servicio

    monkeypatch.setattr(servicio_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    with pytest.raises(PermissionError, match="tecnico asignado"):
        await ServicioServicio(SimpleNamespace()).iniciar(SERVICIO_ID, crear_tecnico_fake())


@pytest.mark.asyncio
async def test_iniciar_servicio_valida_estado_aceptado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico_fake()
    servicio = crear_servicio_fake(estado="DISPONIBLE")
    servicio.tecnico_aceptado_id = tecnico.id

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return servicio

    monkeypatch.setattr(servicio_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    with pytest.raises(ValueError, match="estado ACEPTADO"):
        await ServicioServicio(SimpleNamespace()).iniciar(SERVICIO_ID, tecnico)


@pytest.mark.asyncio
async def test_finalizar_servicio_valida_asignado_y_guarda_fecha_finalizacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico_fake()
    servicio = crear_servicio_fake(estado="EN_PROCESO")
    servicio.tecnico_aceptado_id = tecnico.id
    servicio.fecha_inicio = FECHA

    class SessionFake:
        commits = 0

        async def commit(self) -> None:
            self.__class__.commits += 1

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return servicio

        async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion:
            return ServicioConUbicacion(servicio, 4.711, -74.0721)

    monkeypatch.setattr(servicio_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    respuesta = await ServicioServicio(SessionFake()).finalizar(SERVICIO_ID, tecnico)

    assert respuesta is not None
    assert respuesta.estado == "FINALIZADO"
    assert respuesta.fecha_finalizacion is not None
    assert servicio.fecha_finalizacion is not None
    assert SessionFake.commits == 1


@pytest.mark.asyncio
async def test_finalizar_servicio_valida_estado_en_proceso(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico_fake()
    servicio = crear_servicio_fake(estado="ACEPTADO")
    servicio.tecnico_aceptado_id = tecnico.id

    class ServicioRepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id_para_actualizar(self, servicio_id: UUID) -> SimpleNamespace:
            return servicio

    monkeypatch.setattr(servicio_modulo, "ServicioRepositorio", ServicioRepositorioFake)

    with pytest.raises(ValueError, match="estado EN_PROCESO"):
        await ServicioServicio(SimpleNamespace()).finalizar(SERVICIO_ID, tecnico)
