import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql

os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "clave-local-para-pruebas-con-longitud-segura"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://fedetec:fedetec@localhost:5432/fedetec"

from app.repositorios.tecnico import TecnicoConUbicacion, TecnicoRepositorio
from app.schemas.tecnico import DisponibilidadTecnicoActualizar, UbicacionTecnicoActualizar
from app.servicios import tecnico as tecnico_modulo
from app.servicios.tecnico import TecnicoServicio

TECNICO_ID = UUID("44444444-4444-4444-4444-444444444444")
USUARIO_ID = UUID("55555555-5555-5555-5555-555555555555")
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
