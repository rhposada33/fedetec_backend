import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "clave-local-para-pruebas-con-longitud-segura"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://fedetec:fedetec@localhost:5432/fedetec"

from app.core.storage import UploadUrlGenerada
from app.repositorios.servicio import ServicioConUbicacion
from app.schemas.evidencia_servicio import EvidenciaServicioCrear, EvidenciaUploadUrlSolicitar
from app.servicios import evidencia_servicio as evidencia_modulo
from app.servicios.evidencia_servicio import EvidenciaServicioServicio

SERVICIO_ID = UUID("33333333-3333-3333-3333-333333333333")
TECNICO_ID = UUID("44444444-4444-4444-4444-444444444444")
USUARIO_TECNICO_ID = UUID("55555555-5555-5555-5555-555555555555")
ADMIN_ID = UUID("66666666-6666-6666-6666-666666666666")
EVIDENCIA_ID = UUID("77777777-7777-7777-7777-777777777777")
FECHA = datetime(2026, 5, 28, tzinfo=UTC)


def crear_servicio_fake(tecnico_id: UUID = TECNICO_ID) -> SimpleNamespace:
    return SimpleNamespace(
        id=SERVICIO_ID,
        tecnico_aceptado_id=tecnico_id,
    )


def crear_tecnico_fake(tecnico_id: UUID = TECNICO_ID) -> SimpleNamespace:
    return SimpleNamespace(id=tecnico_id, usuario_id=USUARIO_TECNICO_ID)


def crear_evidencia_fake(estado: str = "PENDIENTE") -> SimpleNamespace:
    return SimpleNamespace(
        id=EVIDENCIA_ID,
        servicio_id=SERVICIO_ID,
        subido_por_usuario_id=USUARIO_TECNICO_ID,
        url_archivo="https://example.com/evidencia.jpg",
        storage_key="evidencias/servicio/evidencia.jpg",
        tipo_archivo="image/jpeg",
        descripcion="Foto final",
        estado_aprobacion=estado,
        aprobado_por_usuario_id=None,
        fecha_aprobacion=None,
        fecha_creacion=FECHA,
    )


class ServicioRepositorioFake:
    servicio = crear_servicio_fake()

    def __init__(self, session: object) -> None:
        self.session = session

    async def obtener_por_id(self, servicio_id: UUID) -> ServicioConUbicacion | None:
        return ServicioConUbicacion(self.servicio, 4.711, -74.0721)


class EvidenciaRepositorioFake:
    evidencia_guardada = None
    evidencia = crear_evidencia_fake()

    def __init__(self, session: object) -> None:
        self.session = session

    async def crear(self, evidencia: object) -> object:
        evidencia.id = EVIDENCIA_ID
        evidencia.fecha_creacion = FECHA
        self.__class__.evidencia_guardada = evidencia
        return evidencia

    async def listar_por_servicio(self, servicio_id: UUID) -> list[object]:
        return [self.evidencia]

    async def obtener_por_id(self, evidencia_id: UUID) -> object | None:
        return self.evidencia

    async def guardar(self, evidencia: object) -> object:
        return evidencia


class ConfiguracionManualFake:
    def __init__(self, session: object) -> None:
        self.session = session

    async def obtener_valor(self, clave: str) -> dict:
        return {"modo": "MANUAL", "roles_permitidos": ["ADMIN"]}


class ConfiguracionAutoFake:
    def __init__(self, session: object) -> None:
        self.session = session

    async def obtener_valor(self, clave: str) -> dict:
        return {"modo": "AUTO"}


class StorageFake:
    content_type = None
    storage_key = None

    async def crear_upload_url(
        self, storage_key: str, content_type: str
    ) -> UploadUrlGenerada:
        self.__class__.storage_key = storage_key
        self.__class__.content_type = content_type
        return UploadUrlGenerada(
            upload_url=f"https://storage.example.com/upload/{storage_key}",
            public_url=f"https://cdn.example.com/{storage_key}",
            storage_key=storage_key,
        )


def parchear_repositorios(
    monkeypatch: pytest.MonkeyPatch, configuracion: type = ConfiguracionManualFake
) -> None:
    monkeypatch.setattr(evidencia_modulo, "ServicioRepositorio", ServicioRepositorioFake)
    monkeypatch.setattr(evidencia_modulo, "EvidenciaServicioRepositorio", EvidenciaRepositorioFake)
    monkeypatch.setattr(evidencia_modulo, "ConfiguracionAppRepositorio", configuracion)


@pytest.mark.asyncio
async def test_crear_evidencia_asignada_crea_registro_pendiente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parchear_repositorios(monkeypatch)

    evidencia = await EvidenciaServicioServicio(object()).crear(
        SERVICIO_ID,
        crear_tecnico_fake(),
        EvidenciaServicioCrear(
            url_archivo="https://example.com/evidencia.jpg",
            tipo_archivo="image/jpeg",
            descripcion="Foto final",
        ),
    )

    assert evidencia is not None
    assert evidencia.url_archivo == "https://example.com/evidencia.jpg"
    assert evidencia.storage_key is None
    assert evidencia.tipo_archivo == "image/jpeg"
    assert evidencia.descripcion == "Foto final"
    assert evidencia.estado_aprobacion == "PENDIENTE"
    assert evidencia.subido_por_usuario_id == USUARIO_TECNICO_ID


@pytest.mark.asyncio
async def test_crear_evidencia_rechaza_tecnico_no_asignado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parchear_repositorios(monkeypatch)

    with pytest.raises(PermissionError, match="tecnico asignado"):
        await EvidenciaServicioServicio(object()).crear(
            SERVICIO_ID,
            crear_tecnico_fake(UUID("88888888-8888-8888-8888-888888888888")),
            EvidenciaServicioCrear(url_archivo="https://example.com/evidencia.jpg"),
        )


@pytest.mark.asyncio
async def test_configuracion_auto_aprueba_evidencia_al_crear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parchear_repositorios(monkeypatch, ConfiguracionAutoFake)

    evidencia = await EvidenciaServicioServicio(object()).crear(
        SERVICIO_ID,
        crear_tecnico_fake(),
        EvidenciaServicioCrear(url_archivo="https://example.com/evidencia.jpg"),
    )

    assert evidencia is not None
    assert evidencia.estado_aprobacion == "APROBADA"
    assert evidencia.aprobado_por_usuario_id == USUARIO_TECNICO_ID
    assert evidencia.fecha_aprobacion is not None


@pytest.mark.asyncio
async def test_upload_url_evidencia_tecnico_asignado_responde_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parchear_repositorios(monkeypatch)

    respuesta = await EvidenciaServicioServicio(object(), StorageFake()).crear_upload_url(
        SERVICIO_ID,
        crear_tecnico_fake(),
        EvidenciaUploadUrlSolicitar(
            filename="gps instalado.jpg",
            content_type="image/jpeg",
        ),
    )

    assert respuesta is not None
    assert respuesta.storage_key.startswith(f"evidencias/{SERVICIO_ID}/")
    assert respuesta.storage_key.endswith("-gps-instalado.jpg")
    assert respuesta.upload_url == f"https://storage.example.com/upload/{respuesta.storage_key}"
    assert respuesta.public_url == f"https://cdn.example.com/{respuesta.storage_key}"
    assert StorageFake.content_type == "image/jpeg"


@pytest.mark.asyncio
async def test_upload_url_evidencia_rechaza_tecnico_no_asignado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parchear_repositorios(monkeypatch)

    with pytest.raises(PermissionError, match="tecnico asignado"):
        await EvidenciaServicioServicio(object(), StorageFake()).crear_upload_url(
            SERVICIO_ID,
            crear_tecnico_fake(UUID("88888888-8888-8888-8888-888888888888")),
            EvidenciaUploadUrlSolicitar(
                filename="gps-installed.jpg",
                content_type="image/jpeg",
            ),
        )


@pytest.mark.asyncio
async def test_upload_url_evidencia_rechaza_tipo_archivo_invalido(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parchear_repositorios(monkeypatch)

    with pytest.raises(ValueError, match="Tipo de archivo"):
        await EvidenciaServicioServicio(object(), StorageFake()).crear_upload_url(
            SERVICIO_ID,
            crear_tecnico_fake(),
            EvidenciaUploadUrlSolicitar(
                filename="script.exe",
                content_type="application/x-msdownload",
            ),
        )


@pytest.mark.asyncio
async def test_upload_url_evidencia_retorna_none_si_servicio_no_existe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ServicioRepositorioNoEncontradoFake(ServicioRepositorioFake):
        async def obtener_por_id(self, servicio_id: UUID) -> None:
            return None

    parchear_repositorios(monkeypatch)
    monkeypatch.setattr(
        evidencia_modulo, "ServicioRepositorio", ServicioRepositorioNoEncontradoFake
    )

    respuesta = await EvidenciaServicioServicio(object(), StorageFake()).crear_upload_url(
        SERVICIO_ID,
        crear_tecnico_fake(),
        EvidenciaUploadUrlSolicitar(
            filename="gps-installed.jpg",
            content_type="image/png",
        ),
    )

    assert respuesta is None


@pytest.mark.asyncio
async def test_admin_aprueba_y_rechaza_evidencia(monkeypatch: pytest.MonkeyPatch) -> None:
    parchear_repositorios(monkeypatch)
    admin = SimpleNamespace(id=ADMIN_ID)
    servicio = EvidenciaServicioServicio(object())

    aprobada = await servicio.aprobar(EVIDENCIA_ID, admin)
    assert aprobada is not None
    assert aprobada.estado_aprobacion == "APROBADA"
    assert aprobada.aprobado_por_usuario_id == ADMIN_ID
    assert aprobada.fecha_aprobacion is not None

    rechazada = await servicio.rechazar(EVIDENCIA_ID, admin)
    assert rechazada is not None
    assert rechazada.estado_aprobacion == "RECHAZADA"
    assert rechazada.aprobado_por_usuario_id == ADMIN_ID
