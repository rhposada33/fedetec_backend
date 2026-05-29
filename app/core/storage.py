from dataclasses import dataclass
from urllib.parse import quote

from app.core.config import settings


@dataclass(frozen=True)
class UploadUrlGenerada:
    upload_url: str
    public_url: str
    storage_key: str


class ProveedorStorage:
    async def crear_upload_url(self, storage_key: str, content_type: str) -> UploadUrlGenerada:
        raise NotImplementedError


class ProveedorStorageLocal(ProveedorStorage):
    async def crear_upload_url(self, storage_key: str, content_type: str) -> UploadUrlGenerada:
        key_url = quote(storage_key)
        # TODO: reemplazar por URLs firmadas de S3, Supabase Storage o Firebase Storage.
        return UploadUrlGenerada(
            upload_url=f"{settings.STORAGE_UPLOAD_BASE_URL.rstrip('/')}/{key_url}",
            public_url=f"{settings.STORAGE_PUBLIC_BASE_URL.rstrip('/')}/{key_url}",
            storage_key=storage_key,
        )


def obtener_proveedor_storage() -> ProveedorStorage:
    return ProveedorStorageLocal()
