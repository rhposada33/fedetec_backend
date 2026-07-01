from email.message import EmailMessage

import pytest

from app.core.config import settings
from app.core.correo import ServicioCorreo


@pytest.mark.asyncio
async def test_correo_no_envia_si_smtp_esta_deshabilitado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "SMTP_HABILITADO", False)
    enviado = await ServicioCorreo().enviar_bienvenida("usuario@example.com", "Usuario")
    assert enviado is False


@pytest.mark.asyncio
async def test_correo_envia_mensaje_con_smtp_configurado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mensajes: list[EmailMessage] = []
    monkeypatch.setattr(settings, "SMTP_HABILITADO", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_REMITENTE", "no-reply@example.com")
    monkeypatch.setattr(
        ServicioCorreo,
        "_enviar_smtp",
        lambda _self, mensaje: mensajes.append(mensaje),
    )

    enviado = await ServicioCorreo().enviar_bienvenida("usuario@example.com", "Usuario")

    assert enviado is True
    assert len(mensajes) == 1
    assert mensajes[0]["To"] == "usuario@example.com"
    assert mensajes[0]["Subject"] == "Bienvenido a FEDETEC"


@pytest.mark.asyncio
async def test_falla_smtp_no_propaga_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HABILITADO", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_REMITENTE", "no-reply@example.com")

    def fallar(_self: ServicioCorreo, _mensaje: EmailMessage) -> None:
        raise OSError("SMTP no disponible")

    monkeypatch.setattr(ServicioCorreo, "_enviar_smtp", fallar)
    enviado = await ServicioCorreo().enviar_bienvenida("usuario@example.com", "Usuario")
    assert enviado is False
