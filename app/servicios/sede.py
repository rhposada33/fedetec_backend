from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.sede import Sede
from app.repositorios.sede import SedeRepositorio
from app.schemas.sede import SedeCrear


class SedeServicio:
    def __init__(self, session: AsyncSession) -> None:
        self.sedes = SedeRepositorio(session)

    async def listar(self) -> list[Sede]:
        return await self.sedes.listar()

    async def crear(self, sede_in: SedeCrear) -> Sede:
        ubicacion = None
        if sede_in.latitud is not None and sede_in.longitud is not None:
            ubicacion = WKTElement(f"POINT({sede_in.longitud} {sede_in.latitud})", srid=4326)

        sede = Sede(nombre=sede_in.nombre, direccion=sede_in.direccion, ubicacion=ubicacion)
        return await self.sedes.crear(sede)

