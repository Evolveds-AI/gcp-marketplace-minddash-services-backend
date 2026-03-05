import time
from typing import Any, Dict, Optional

from google.cloud import storage

# Caches simples en memoria
_SEMANTIC_CACHE: Dict[str, Dict[str, Any]] = {}


def get_cached_semantic(gs_uri: str, ttl_seconds: int = 900) -> Optional[str]:
    """Devuelve el YAML cacheado si no expiró; si expiró, None."""
    entry = _SEMANTIC_CACHE.get(gs_uri)
    now = time.time()
    if entry and (now - entry.get("loaded_at", 0)) <= ttl_seconds:
        return entry.get("content")
    return None


def set_cached_semantic(gs_uri: str, content: str) -> None:
    _SEMANTIC_CACHE[gs_uri] = {"content": content, "loaded_at": time.time()}


def upload_text_to_gcs(
    bucket_name: str,
    destination_path: str,
    content: str,
    content_type: str = "text/yaml",
) -> str:
    """Sube texto a GCS y devuelve URL pública si es posible o gs:// si no."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_path)
    blob.upload_from_string(content, content_type=content_type)
    # Hacer público opcionalmente según política del bucket
    try:
        blob.make_public()
        return blob.public_url
    except Exception:
        # Si no es público, devolver URL de gs:// o signed URL si se requiere más adelante
        return f"gs://{bucket_name}/{destination_path}"


def upload_bytes_to_gcs(
    bucket_name: str,
    destination_path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """Sube bytes a GCS y devuelve URL pública si es posible o gs:// si no."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_path)
    blob.upload_from_string(data, content_type=content_type)
    try:
        blob.make_public()
        return blob.public_url
    except Exception:
        return f"gs://{bucket_name}/{destination_path}"


def download_text_from_gcs(bucket_name: str, object_path: str) -> tuple[str, str]:
    """Descarga un objeto como texto. Devuelve (contenido, content_type). Requiere credenciales de servicio."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_path)
    data = blob.download_as_text(encoding="utf-8")
    content_type = blob.content_type or "text/plain"
    return data, content_type


def delete_gcs_object(bucket_name: str, object_path: str) -> None:
    """Elimina un objeto de GCS. No falla si no existe (idempotente)."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_path)
    try:
        blob.delete()
    except Exception:
        # Ignorar errores de no encontrado o permisos, el endpoint puede continuar
        pass
