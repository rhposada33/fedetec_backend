import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verificar_password(password_plano: str, password_hash: str) -> bool:
    return pwd_context.verify(password_plano, password_hash)


def generar_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def generar_api_key() -> str:
    return f"fedetec_{secrets.token_urlsafe(32)}"


def generar_api_key_hash(api_key: str) -> str:
    return pwd_context.hash(api_key)


def verificar_api_key(api_key: str, api_key_hash: str) -> bool:
    return pwd_context.verify(api_key, api_key_hash)


def crear_token_acceso(subject: str | int, expires_delta: timedelta | None = None) -> str:
    expira = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {"sub": str(subject), "exp": expira}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise ValueError("Token invalido") from exc
