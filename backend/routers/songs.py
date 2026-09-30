from fastapi import APIRouter, Depends, HTTPException, Query, status

from .. import bigquery_repo as repo
from ..models import EstadoValor, Song, SongCreate, SongUpdate
from ..security import require_api_key
from ..services import filtrar_canciones, texto_catalogo

router = APIRouter(prefix="/api/songs", tags=["canciones"])


@router.get("", response_model=list[Song])
def listar_canciones(
    search: str | None = Query(
        default=None,
        description="Filtra por nombre o número de canción."
    ),
    estado: EstadoValor | None = Query(
        default=None,
        description="Filtra por estado."
    )
):
    return filtrar_canciones(repo.list_songs(), search=search, estado=estado)


# Va antes de /{numero}: si no, el path param entero rechazaría la ruta.
@router.get("/texto-compartir")
def texto_para_compartir_canciones():
    """Texto del repertorio para pegar en el chat (solo estado OK)."""
    canciones = filtrar_canciones(repo.list_songs(), estado="OK")

    return {"texto": texto_catalogo(canciones)}


@router.get("/{numero}", response_model=Song)
def obtener_cancion(numero: int):
    song = repo.get_song(numero)

    if song is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe la canción N° {numero}."
        )

    return song


@router.post(
    "",
    response_model=list[Song],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)]
)
def crear_canciones(payload: SongCreate | list[SongCreate]):
    """Alta de canciones. Acepta un objeto o una lista de objetos."""
    canciones = payload if isinstance(payload, list) else [payload]

    if not canciones:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se recibió ninguna canción."
        )

    # Secuencial a propósito: cada alta necesita el MAX(Numero) de la anterior.
    return [repo.insert_song(song.model_dump()) for song in canciones]


@router.patch(
    "/{numero}",
    response_model=Song,
    dependencies=[Depends(require_api_key)]
)
def actualizar_cancion(numero: int, cambios: SongUpdate):
    changes = cambios.model_dump(exclude_unset=True)

    if not repo.update_song(numero, changes):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe la canción N° {numero}."
        )

    return repo.get_song(numero)


@router.delete(
    "/{numero}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)]
)
def eliminar_cancion(numero: int):
    if not repo.delete_song(numero):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe la canción N° {numero}."
        )
