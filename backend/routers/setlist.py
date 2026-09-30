from fastapi import APIRouter, Depends, HTTPException, status

from .. import bigquery_repo as repo
from ..models import SetlistPublish, SetlistResponse
from ..security import require_api_key
from ..services import listado_desde_setlist, texto_para_compartir

router = APIRouter(prefix="/api/setlist", tags=["listado"])


def _armar_respuesta() -> SetlistResponse:
    setlist = repo.get_setlist()

    if not setlist:
        return SetlistResponse()

    listado, faltantes = listado_desde_setlist(repo.list_songs(), setlist)

    return SetlistResponse(
        canciones=listado,
        faltantes=faltantes,
        publicado=max(item["Fecha_Creacion"] for item in setlist),
        texto_compartir=texto_para_compartir(listado)
    )


@router.get("", response_model=SetlistResponse)
def obtener_listado():
    return _armar_respuesta()


@router.put(
    "",
    response_model=SetlistResponse,
    dependencies=[Depends(require_api_key)]
)
def publicar_listado(payload: SetlistPublish):
    """Reemplaza el listado publicado. Admite números repetidos."""
    existentes = {song["Numero"] for song in repo.list_songs()}

    desconocidos = [n for n in payload.numeros if n not in existentes]

    if desconocidos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No existen las canciones N° "
                + ", ".join(str(n) for n in dict.fromkeys(desconocidos))
                + "."
            )
        )

    repo.replace_setlist(payload.numeros)

    return _armar_respuesta()


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)]
)
def limpiar_listado():
    repo.clear_setlist()
