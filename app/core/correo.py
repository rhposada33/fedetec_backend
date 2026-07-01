import asyncio
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings

logger = logging.getLogger(__name__)


class ServicioCorreo:
    async def enviar_bienvenida(self, destinatario: str, nombre: str) -> bool:
        asunto = "Bienvenido a FEDETEC"
        contenido = (
            f"Hola {nombre},\n\n"
            "Tu usuario fue creado correctamente en la plataforma FEDETEC. "
            "Ya puedes iniciar sesión con las credenciales que te fueron asignadas.\n\n"
            "Por seguridad, este correo no incluye tu contraseña."
        )
        return await self.enviar(destinatario, asunto, contenido)

    async def enviar_cambio_estado_servicio(
        self, destinatario: str, nombre_empresa: str, servicio_id: str, estado: str
    ) -> bool:
        asunto = f"Actualización de servicio: {estado.replace('_', ' ').title()}"
        contenido = (
            f"Hola {nombre_empresa},\n\n"
            f"El servicio {servicio_id} cambió al estado "
            f"{estado.replace('_', ' ').lower()}.\n\n"
            "Puedes consultar el detalle actualizado en el portal de empresas FEDETEC."
        )
        return await self.enviar(destinatario, asunto, contenido)

    async def enviar(self, destinatario: str, asunto: str, contenido: str) -> bool:
        if not settings.SMTP_HABILITADO:
            logger.info("Correo omitido porque SMTP_HABILITADO=false: %s", asunto)
            return False
        if not settings.SMTP_HOST or not settings.SMTP_REMITENTE:
            logger.error("SMTP habilitado sin SMTP_HOST o SMTP_REMITENTE")
            return False

        mensaje = EmailMessage()
        mensaje["Subject"] = asunto
        mensaje["From"] = formataddr(("FEDETEC", settings.SMTP_REMITENTE))
        mensaje["To"] = destinatario
        mensaje.set_content(contenido)

        try:
            await asyncio.to_thread(self._enviar_smtp, mensaje)
        except (OSError, smtplib.SMTPException) as exc:
            logger.exception("No fue posible enviar correo a %s: %s", destinatario, exc)
            return False
        return True

    @staticmethod
    def _enviar_smtp(mensaje: EmailMessage) -> None:
        cliente_cls = smtplib.SMTP_SSL if settings.SMTP_USAR_SSL else smtplib.SMTP
        with cliente_cls(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as cliente:
            if settings.SMTP_USAR_TLS and not settings.SMTP_USAR_SSL:
                cliente.starttls()
            if settings.SMTP_USUARIO:
                cliente.login(settings.SMTP_USUARIO, settings.SMTP_PASSWORD)
            cliente.send_message(mensaje)


servicio_correo = ServicioCorreo()
