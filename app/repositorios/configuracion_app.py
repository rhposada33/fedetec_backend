from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.configuracion_app import ConfiguracionApp


class ConfiguracionAppRepositorio:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def obtener_valor(self, clave: str) -> dict | None:
        configuracion = await self.session.get(ConfiguracionApp, clave)
        return configuracion.valor if configuracion is not None else None

    async def guardar_valor(self, clave: str, valor: dict) -> ConfiguracionApp:
        configuracion = await self.session.get(ConfiguracionApp, clave)
        if configuracion is None:
            configuracion = ConfiguracionApp(clave=clave, valor=valor)
            self.session.add(configuracion)
        else:
            configuracion.valor = valor

        await self.session.commit()
        await self.session.refresh(configuracion)
        return configuracion
