import hmac

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from .config import settings

_api_key_header = APIKeyHeader(name="X-API-Key")


def require_api_key(api_key: str = Security(_api_key_header)) -> str:
    if not hmac.compare_digest(api_key, settings.internal_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key
