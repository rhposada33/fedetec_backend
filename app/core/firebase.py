import asyncio
import base64
import json
import logging

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings

logger = logging.getLogger(__name__)


class FirebaseMensajeria:
    def __init__(self) -> None:
        self._app = None

    def _obtener_app(self):
        if self._app is not None:
            return self._app
        if not settings.FIREBASE_HABILITADO:
            return None
        opciones = {"projectId": settings.FIREBASE_PROJECT_ID}
        if settings.FIREBASE_CREDENTIALS_JSON_BASE64:
            datos = json.loads(
                base64.b64decode(settings.FIREBASE_CREDENTIALS_JSON_BASE64).decode("utf-8")
            )
            credencial = credentials.Certificate(datos)
            self._app = firebase_admin.initialize_app(credencial, opciones, name="fedetec")
        else:
            self._app = firebase_admin.initialize_app(options=opciones, name="fedetec")
        return self._app

    async def enviar_servicio(self, token: str, notificacion_id: str, servicio_id: str) -> str:
        app = self._obtener_app()
        if app is None:
            raise RuntimeError("Firebase no está habilitado")
        mensaje = messaging.Message(
            token=token,
            notification=messaging.Notification(
                title="Nuevo servicio disponible",
                body="Hay un nuevo servicio cerca de tu ubicación.",
            ),
            data={"notificacion_id": notificacion_id, "servicio_id": servicio_id},
            android=messaging.AndroidConfig(priority="high"),
        )
        return await asyncio.to_thread(messaging.send, mensaje, app=app)


firebase_mensajeria = FirebaseMensajeria()
