import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql

os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "clave-local-para-pruebas-con-longitud-segura"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://fedetec:fedetec@localhost:5432/fedetec"

from app.repositorios.notificacion_servicio import NotificacionServicioRepositorio
from app.repositorios.tecnico import TecnicoConUbicacion, TecnicoRepositorio
from app.schemas.tecnico import DisponibilidadTecnicoActualizar, UbicacionTecnicoActualizar
from app.servicios import tecnico as tecnico_modulo
from app.servicios.tecnico import TecnicoServicio

TECNICO_ID = UUID("44444444-4444-4444-4444-444444444444")
USUARIO_ID = UUID("55555555-5555-5555-5555-555555555555")
SERVICIO_ID = UUID("66666666-6666-6666-6666-666666666666")
EMPRESA_ID = UUID("77777777-7777-7777-7777-777777777777")
NOTIFICACION_ID = UUID("88888888-8888-8888-8888-888888888888")
FECHA = datetime(2026, 5, 28, tzinfo=UTC)


def crear_tecnico(esta_disponible: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id=TECNICO_ID,
        usuario_id=USUARIO_ID,
        usuario=SimpleNamespace(
            nombre_completo="Tecnico Demo",
            correo="tecnico@example.com",
            telefono="3001234567",
        ),
        ubicacion_actual=None,
        esta_disponible=esta_disponible,
        fecha_ultima_ubicacion=None,
        fecha_creacion=FECHA,
    )


def crear_servicio(estado: str = "DISPONIBLE") -> SimpleNamespace:
    return SimpleNamespace(
        id=SERVICIO_ID,
        empresa_cliente_id=EMPRESA_ID,
        tipo_servicio=1,
        placa_vehiculo="ABC123",
        direccion="Calle 123",
        fecha_programada=FECHA,
        estado=estado,
        clave_idempotencia="idem-1",
        tecnico_aceptado_id=None,
        fecha_aceptacion=None,
        fecha_inicio=None,
        fecha_finalizacion=None,
        fecha_creacion=FECHA,
        fecha_actualizacion=FECHA,
    )


def crear_notificacion(estado: str = "ENVIADA") -> SimpleNamespace:
    return SimpleNamespace(
        id=NOTIFICACION_ID,
        servicio_id=SERVICIO_ID,
        tecnico_id=TECNICO_ID,
        estado=estado,
        fecha_envio=FECHA,
        fecha_lectura=None,
        servicio=crear_servicio(),
    )


@pytest.mark.asyncio
async def test_actualizar_ubicacion_guarda_point_gps(monkeypatch: pytest.MonkeyPatch) -> None:
    tecnico = crear_tecnico()

    class RepositorioFake:
        ubicacion_guardada: str | None = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def guardar(self, tecnico_actualizado: SimpleNamespace) -> SimpleNamespace:
            self.__class__.ubicacion_guardada = tecnico_actualizado.ubicacion_actual.desc
            return tecnico_actualizado

        async def obtener_por_id(self, tecnico_id: UUID) -> TecnicoConUbicacion | None:
            return TecnicoConUbicacion(tecnico, 4.711, -74.0721)

    monkeypatch.setattr(tecnico_modulo, "TecnicoRepositorio", RepositorioFake)

    respuesta = await TecnicoServicio(object()).actualizar_ubicacion(
        tecnico, UbicacionTecnicoActualizar(latitud=4.711, longitud=-74.0721)
    )

    assert RepositorioFake.ubicacion_guardada == "POINT(-74.0721 4.711)"
    assert tecnico.fecha_ultima_ubicacion is not None
    assert respuesta.latitud == 4.711
    assert respuesta.longitud == -74.0721


@pytest.mark.asyncio
async def test_actualizar_disponibilidad_persiste_estado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico()

    class RepositorioFake:
        disponibilidad_guardada: bool | None = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def guardar(self, tecnico_actualizado: SimpleNamespace) -> SimpleNamespace:
            self.__class__.disponibilidad_guardada = tecnico_actualizado.esta_disponible
            return tecnico_actualizado

        async def obtener_por_id(self, tecnico_id: UUID) -> TecnicoConUbicacion | None:
            return TecnicoConUbicacion(tecnico, None, None)

    monkeypatch.setattr(tecnico_modulo, "TecnicoRepositorio", RepositorioFake)

    respuesta = await TecnicoServicio(object()).actualizar_disponibilidad(
        tecnico, DisponibilidadTecnicoActualizar(esta_disponible=False)
    )

    assert RepositorioFake.disponibilidad_guardada is False
    assert respuesta.esta_disponible is False


@pytest.mark.asyncio
async def test_busqueda_cercanos_usa_postgis_disponibilidad_y_orden() -> None:
    class ResultadoFake:
        def all(self) -> list[object]:
            return []

    class SessionFake:
        statement = None

        async def execute(self, statement: object) -> ResultadoFake:
            self.__class__.statement = statement
            return ResultadoFake()

    session = SessionFake()

    await TecnicoRepositorio(session).buscar_cercanos(4.711, -74.0721, 5000)

    sql = str(
        SessionFake.statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}
        )
    )

    assert "ST_DWithin" in sql
    assert "ST_Distance" in sql
    assert "tecnicos.esta_disponible IS true" in sql
    assert "tecnicos.ubicacion_actual IS NOT NULL" in sql
    assert "ORDER BY ST_Distance" in sql


@pytest.mark.asyncio
async def test_servicios_disponibles_tecnico_salen_de_notificaciones_visibles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico()
    notificacion = crear_notificacion()

    class RepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def listar_servicios_disponibles_para_tecnico(
            self, tecnico_id: UUID
        ) -> list[SimpleNamespace]:
            assert tecnico_id == TECNICO_ID
            return [
                SimpleNamespace(
                    notificacion=notificacion,
                    latitud=4.711,
                    longitud=-74.0721,
                )
            ]

    monkeypatch.setattr(tecnico_modulo, "NotificacionServicioRepositorio", RepositorioFake)

    respuesta = await TecnicoServicio(object()).listar_servicios_disponibles(tecnico)

    assert len(respuesta) == 1
    assert respuesta[0].id == SERVICIO_ID
    assert respuesta[0].estado == "DISPONIBLE"
    assert respuesta[0].latitud == 4.711
    assert respuesta[0].longitud == -74.0721


@pytest.mark.asyncio
async def test_notificaciones_tecnico_incluyen_servicio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico()
    notificacion = crear_notificacion()

    class RepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def listar_para_tecnico(self, tecnico_id: UUID) -> list[SimpleNamespace]:
            assert tecnico_id == TECNICO_ID
            return [
                SimpleNamespace(
                    notificacion=notificacion,
                    latitud=4.711,
                    longitud=-74.0721,
                )
            ]

    monkeypatch.setattr(tecnico_modulo, "NotificacionServicioRepositorio", RepositorioFake)

    respuesta = await TecnicoServicio(object()).listar_notificaciones(tecnico)

    assert len(respuesta) == 1
    assert respuesta[0].id == NOTIFICACION_ID
    assert respuesta[0].estado == "ENVIADA"
    assert respuesta[0].servicio.id == SERVICIO_ID


@pytest.mark.asyncio
async def test_servicios_disponibles_filtra_por_notificacion_visible_y_estado() -> None:
    class ResultadoFake:
        def all(self) -> list[object]:
            return []

    class SessionFake:
        statement = None

        async def execute(self, statement: object) -> ResultadoFake:
            self.__class__.statement = statement
            return ResultadoFake()

    await NotificacionServicioRepositorio(
        SessionFake()
    ).listar_servicios_disponibles_para_tecnico(TECNICO_ID)

    sql = str(
        SessionFake.statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}
        )
    )

    assert "notificaciones_servicio.tecnico_id" in sql
    assert "notificaciones_servicio.estado IN" in sql
    assert "servicios.estado = " in sql
    assert "ORDER BY notificaciones_servicio.fecha_envio DESC" in sql
