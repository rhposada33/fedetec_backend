from functools import lru_cache
from typing import Annotated

from pydantic import AnyHttpUrl, Field, TypeAdapter, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    APP_NOMBRE: str = "Fedetec API"
    APP_ENTORNO: str = "local"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str
    BACKEND_CORS_ORIGINS: Annotated[list[str], NoDecode] = []

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parsear_cors(cls, valor: str | list[str]) -> list[str]:
        if isinstance(valor, str):
            return [origen.strip() for origen in valor.split(",") if origen.strip()]
        return valor

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def validar_cors(cls, valor: list[str]) -> list[str]:
        adaptador = TypeAdapter(AnyHttpUrl)
        for origen in valor:
            adaptador.validate_python(origen)
        return valor


@lru_cache
def obtener_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = obtener_settings()
