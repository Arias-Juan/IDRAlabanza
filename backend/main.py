import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError

from .config import get_settings
from .routers import setlist, songs
from .security import require_api_key

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="Alabanza IDR",
    description=(
        "API del repertorio de alabanza IDR. Las lecturas son públicas; "
        "las escrituras requieren el header X-API-Key."
    ),
    version="2.0.0"
)


@app.exception_handler(GoogleAPIError)
async def bigquery_error_handler(request: Request, exc: GoogleAPIError):
    """Los errores de BigQuery no deben filtrar detalles al cliente."""
    logger.exception("Error de BigQuery en %s", request.url.path)

    return JSONResponse(
        status_code=502,
        content={"detail": "Error de conexión con BigQuery."}
    )


@app.exception_handler(GoogleAuthError)
async def auth_error_handler(request: Request, exc: GoogleAuthError):
    """Falta el ADC en local o la service account en Cloud Run."""
    logger.exception("Error de credenciales en %s", request.url.path)

    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "El servicio no tiene credenciales de GCP. En local, correr "
                "`gcloud auth application-default login`; en Cloud Run, "
                "revisar la service account del servicio."
            )
        }
    )


# Va bajo /api porque el frontend de Google intercepta /healthz en los
# dominios *.run.app y nunca llega a la app. /healthz se deja para cuando
# corre en local o detrás de un dominio propio.
@app.get("/api/healthz", tags=["infra"])
@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}


@app.post("/api/auth/check", tags=["infra"])
def auth_check(_: str = Depends(require_api_key)):
    """Valida la API key que ingresa el admin en el navegador."""
    return {"ok": True}


@app.get("/api/config", tags=["infra"])
def config():
    settings = get_settings()

    return {
        "setlist_ttl_days": settings.setlist_ttl_days,
        "escritura_habilitada": bool(settings.api_keys)
    }


app.include_router(songs.router)
app.include_router(setlist.router)

class NoCacheStaticFiles(StaticFiles):
    """Estáticos que el navegador revalida siempre.

    Sin esto, un navegador puede quedarse con el app.js viejo y el
    index.html nuevo (o al revés) después de un deploy, y la página rompe.
    `no-cache` no significa "no guardar": el archivo se cachea igual, pero
    se revalida contra el ETag, así que lo normal es un 304 sin cuerpo.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)

        response.headers["Cache-Control"] = "no-cache"

        return response


# El frontend se sirve desde el mismo contenedor: mismo origen, sin CORS.
# Va último para que no tape las rutas de /api.
app.mount(
    "/",
    NoCacheStaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend"
)
