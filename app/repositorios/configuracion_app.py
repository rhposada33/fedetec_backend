from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.configuracion_app import ConfiguracionApp


class ConfiguracionAppRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def obtener_valor(self, clave: str) -> dict | None:
        configuracion = await self.session.get(ConfiguracionApp, clave)
        return configuracion.valor if configuracion is not None else None
