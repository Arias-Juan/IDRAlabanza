import hmac

from fastapi import Header, HTTPException, status

from .config import get_settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    """Dependencia para los endpoints de escritura.

    Fail-closed: si no hay ninguna key configurada, la escritura queda
    deshabilitada en vez de quedar abierta.
    """
    keys = get_settings().api_keys

    if not keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Escritura deshabilitada: falta configurar API_KEYS "
                "en el entorno."
            )
        )

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el header X-API-Key.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # compare_digest sobre todas las keys, sin cortar al primer match, para
    # no filtrar por tiempo cuál de ellas coincidió.
    valid = False

    for key in keys:
        if hmac.compare_digest(x_api_key, key):
            valid = True

    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    return x_api_key
