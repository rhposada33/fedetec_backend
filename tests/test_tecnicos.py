import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError

os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "clave-local-para-pruebas-con-longitud-segura"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://fedetec:fedetec@localhost:5432/fedetec"

from app.repositorios.notificacion_servicio import NotificacionServicioRepositorio
from app.repositorios.servicio import ServicioDetalleTecnico, ServicioListaTecnico
from app.repositorios.tecnico import (
    MetricasRendimientoTecnico,
    TecnicoConUbicacion,
    TecnicoRepositorio,
)
from app.schemas.tecnico import (
    DisponibilidadTecnicoActualizar,
    TecnicoActualizar,
    UbicacionTecnicoActualizar,
)
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
            numero_documento=None,
            ciudad=None,
            municipio=None,
            direccion=None,
            eps=None,
            arl=None,
            tiene_vehiculo=False,
            placa_vehiculo=None,
            esta_activo=True,
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
        empresa_cliente=SimpleNamespace(nombre="Transportes del Valle S.A.S."),
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
async def test_actualizar_tecnico_admin_actualiza_usuario_disponibilidad_y_gps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico()

    class RepositorioFake:
        ubicacion_guardada: str | None = None

        def __init__(self, session: object) -> None:
            self.session = session

        async def guardar(self, tecnico_actualizado: SimpleNamespace) -> SimpleNamespace:
            self.__class__.ubicacion_guardada = tecnico_actualizado.ubicacion_actual.desc
            return tecnico_actualizado

        async def obtener_por_id(self, tecnico_id: UUID) -> TecnicoConUbicacion | None:
            return TecnicoConUbicacion(tecnico, 4.72, -74.08)

    monkeypatch.setattr(tecnico_modulo, "TecnicoRepositorio", RepositorioFake)

    respuesta = await TecnicoServicio(object()).actualizar_admin(
        TECNICO_ID,
        TecnicoActualizar(
            nombre_completo="Tecnico Actualizado",
            correo="nuevo@example.com",
            telefono="3007654321",
            ciudad="Bogota",
            esta_disponible=False,
            latitud=4.72,
            longitud=-74.08,
        ),
    )

    assert respuesta is not None
    assert respuesta.nombre_completo == "Tecnico Actualizado"
    assert respuesta.correo == "nuevo@example.com"
    assert respuesta.telefono == "3007654321"
    assert respuesta.ciudad == "Bogota"
    assert respuesta.esta_disponible is False
    assert RepositorioFake.ubicacion_guardada == "POINT(-74.08 4.72)"


@pytest.mark.asyncio
async def test_actualizar_tecnico_admin_rechaza_correo_duplicado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico()

    class SessionFake:
        rollbacks = 0

        async def rollback(self) -> None:
            self.__class__.rollbacks += 1

    class RepositorioFake:
        def __init__(self, session: SessionFake) -> None:
            self.session = session

        async def guardar(self, tecnico_actualizado: SimpleNamespace) -> SimpleNamespace:
            raise IntegrityError("insert", {}, Exception("duplicate"))

        async def obtener_por_id(self, tecnico_id: UUID) -> TecnicoConUbicacion | None:
            return TecnicoConUbicacion(tecnico, None, None)

    monkeypatch.setattr(tecnico_modulo, "TecnicoRepositorio", RepositorioFake)

    with pytest.raises(ValueError, match="correo"):
        await TecnicoServicio(SessionFake()).actualizar_admin(
            TECNICO_ID, TecnicoActualizar(correo="duplicado@example.com")
        )

    assert SessionFake.rollbacks == 1


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
async def test_detalle_servicio_tecnico_permite_servicio_notificado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico()
    servicio = crear_servicio()

    class RepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_detalle_para_tecnico(
            self, servicio_id: UUID, tecnico_id: UUID
        ) -> ServicioDetalleTecnico | None:
            assert servicio_id == SERVICIO_ID
            assert tecnico_id == TECNICO_ID
            return ServicioDetalleTecnico(
                servicio=servicio,
                latitud=3.4516,
                longitud=-76.532,
                distancia_metros=1200.0,
                notificado=True,
            )

    monkeypatch.setattr(tecnico_modulo, "ServicioRepositorio", RepositorioFake)

    respuesta = await TecnicoServicio(object()).obtener_detalle_servicio(tecnico, SERVICIO_ID)

    assert respuesta is not None
    assert respuesta.id == SERVICIO_ID
    assert respuesta.codigo == "SV-66666666"
    assert respuesta.tipo_servicio_nombre == "Mantenimiento"
    assert respuesta.empresa_cliente_nombre == "Transportes del Valle S.A.S."
    assert respuesta.latitud == 3.4516
    assert respuesta.longitud == -76.532
    assert respuesta.distancia_metros == 1200.0


@pytest.mark.asyncio
async def test_detalle_servicio_tecnico_permite_servicio_asignado_sin_notificacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico()
    servicio = crear_servicio(estado="ACEPTADO")
    servicio.tecnico_aceptado_id = TECNICO_ID

    class RepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_detalle_para_tecnico(
            self, servicio_id: UUID, tecnico_id: UUID
        ) -> ServicioDetalleTecnico:
            return ServicioDetalleTecnico(
                servicio=servicio,
                latitud=3.4516,
                longitud=-76.532,
                distancia_metros=None,
                notificado=False,
            )

    monkeypatch.setattr(tecnico_modulo, "ServicioRepositorio", RepositorioFake)

    respuesta = await TecnicoServicio(object()).obtener_detalle_servicio(tecnico, SERVICIO_ID)

    assert respuesta is not None
    assert respuesta.estado == "ACEPTADO"


@pytest.mark.asyncio
async def test_detalle_servicio_tecnico_rechaza_servicio_no_autorizado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico()
    servicio = crear_servicio()
    servicio.tecnico_aceptado_id = UUID("99999999-9999-9999-9999-999999999999")

    class RepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_detalle_para_tecnico(
            self, servicio_id: UUID, tecnico_id: UUID
        ) -> ServicioDetalleTecnico:
            return ServicioDetalleTecnico(
                servicio=servicio,
                latitud=3.4516,
                longitud=-76.532,
                distancia_metros=None,
                notificado=False,
            )

    monkeypatch.setattr(tecnico_modulo, "ServicioRepositorio", RepositorioFake)

    with pytest.raises(PermissionError, match="acceso"):
        await TecnicoServicio(object()).obtener_detalle_servicio(tecnico, SERVICIO_ID)


@pytest.mark.asyncio
async def test_detalle_servicio_tecnico_retorna_none_si_no_existe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico()

    class RepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_detalle_para_tecnico(
            self, servicio_id: UUID, tecnico_id: UUID
        ) -> None:
            return None

    monkeypatch.setattr(tecnico_modulo, "ServicioRepositorio", RepositorioFake)

    respuesta = await TecnicoServicio(object()).obtener_detalle_servicio(tecnico, SERVICIO_ID)

    assert respuesta is None


@pytest.mark.asyncio
async def test_listar_servicios_tecnico_devuelve_items_paginados(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico()
    servicio = crear_servicio(estado="VALIDADO")
    servicio.direccion = "Cra 45 #12-30, Cali"
    servicio.fecha_finalizacion = FECHA

    class RepositorioFake:
        parametros: dict[str, object] = {}

        def __init__(self, session: object) -> None:
            self.session = session

        async def listar_para_tecnico(
            self,
            tecnico_id: UUID,
            estado: str | None = None,
            fecha_desde: datetime | None = None,
            fecha_hasta: datetime | None = None,
            limit: int = 20,
            offset: int = 0,
        ) -> tuple[list[ServicioListaTecnico], int]:
            self.__class__.parametros = {
                "tecnico_id": tecnico_id,
                "estado": estado,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "limit": limit,
                "offset": offset,
            }
            return [
                ServicioListaTecnico(
                    servicio=servicio,
                    latitud=3.4516,
                    longitud=-76.532,
                    distancia_metros=1200.0,
                    calificacion=5,
                )
            ], 1

    monkeypatch.setattr(tecnico_modulo, "ServicioRepositorio", RepositorioFake)

    respuesta = await TecnicoServicio(object()).listar_servicios_tecnico(
        tecnico,
        estado="VALIDADO",
        fecha_desde=FECHA,
        fecha_hasta=FECHA,
        limit=10,
        offset=20,
    )

    assert respuesta.total == 1
    assert respuesta.limit == 10
    assert respuesta.offset == 20
    assert respuesta.items[0].id == SERVICIO_ID
    assert respuesta.items[0].codigo == "SV-66666666"
    assert respuesta.items[0].estado == "VALIDADO"
    assert respuesta.items[0].ciudad == "Cali"
    assert respuesta.items[0].calificacion == 5
    assert RepositorioFake.parametros["tecnico_id"] == TECNICO_ID
    assert RepositorioFake.parametros["estado"] == "VALIDADO"


@pytest.mark.asyncio
async def test_listar_servicios_tecnico_sql_filtra_estado_fecha_y_usuario() -> None:
    class ResultadoFake:
        def all(self) -> list[object]:
            return []

    class SessionFake:
        statement = None

        async def execute(self, statement: object) -> ResultadoFake:
            self.__class__.statement = statement
            return ResultadoFake()

        async def scalar(self, statement: object) -> int:
            return 0

    await tecnico_modulo.ServicioRepositorio(SessionFake()).listar_para_tecnico(
        TECNICO_ID,
        estado="VALIDADO",
        fecha_desde=FECHA,
        fecha_hasta=FECHA,
        limit=10,
        offset=20,
    )

    sql = str(
        SessionFake.statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}
        )
    )

    assert "notificaciones_servicio.tecnico_id" in sql
    assert "servicios.tecnico_aceptado_id = " in sql
    assert "servicios.estado = " in sql
    assert "servicios.fecha_programada >= " in sql
    assert "servicios.fecha_programada <= " in sql
    assert "LIMIT" in sql
    assert "OFFSET" in sql


@pytest.mark.asyncio
async def test_metricas_rendimiento_tecnico_serializa_agregados(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tecnico = crear_tecnico()

    class RepositorioFake:
        def __init__(self, session: object) -> None:
            self.session = session

        async def obtener_por_id(self, tecnico_id: UUID) -> TecnicoConUbicacion | None:
            assert tecnico_id == TECNICO_ID
            return TecnicoConUbicacion(tecnico, None, None)

        async def obtener_metricas_rendimiento(
            self, tecnico_id: UUID
        ) -> MetricasRendimientoTecnico:
            assert tecnico_id == TECNICO_ID
            return MetricasRendimientoTecnico(
                calificacion_promedio=4.5,
                servicios_completados=3,
                servicios_aceptados=5,
                servicios_rechazados=2,
            )

    monkeypatch.setattr(tecnico_modulo, "TecnicoRepositorio", RepositorioFake)

    respuesta = await TecnicoServicio(object()).obtener_metricas_rendimiento(TECNICO_ID)

    assert respuesta is not None
    assert respuesta.tecnico_id == TECNICO_ID
    assert respuesta.calificacion_promedio == 4.5
    assert respuesta.servicios_completados == 3
    assert respuesta.servicios_aceptados == 5
    assert respuesta.servicios_rechazados == 2


@pytest.mark.asyncio
async def test_metricas_rendimiento_tecnico_usa_agregados_sql() -> None:
    class SessionFake:
        statements = []
        resultados = [5, 3, 2, 4.5]

        async def scalar(self, statement: object) -> object:
            self.__class__.statements.append(statement)
            return self.__class__.resultados.pop(0)

    respuesta = await TecnicoRepositorio(SessionFake()).obtener_metricas_rendimiento(
        TECNICO_ID
    )

    sql = [
        str(
            statement.compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}
            )
        )
        for statement in SessionFake.statements
    ]

    assert respuesta.servicios_aceptados == 5
    assert respuesta.servicios_completados == 3
    assert respuesta.servicios_rechazados == 2
    assert respuesta.calificacion_promedio == 4.5
    assert "servicios.tecnico_aceptado_id = " in sql[0]
    assert "servicios.estado IN" in sql[1]
    assert "rechazos_servicio.tecnico_id = " in sql[2]
    assert "avg(calificaciones_servicio.puntuacion)" in sql[3]


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
