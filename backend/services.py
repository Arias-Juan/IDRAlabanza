"""Lógica de negocio portada de la app Streamlit."""


def listado_desde_setlist(
    songs: list[dict],
    setlist: list[dict]
) -> tuple[list[dict], list[int]]:
    """Arma el listado en orden, salteando canciones borradas de la base.

    Devuelve (listado, faltantes). Los números repetidos se conservan.
    """
    por_numero = {song["Numero"]: song for song in songs}

    listado = []
    faltantes = []

    for item in setlist:
        numero = item["Numero"]

        if numero in por_numero:
            listado.append(por_numero[numero])

        else:
            faltantes.append(numero)

    # dict.fromkeys: sin repetidos, conservando el orden de aparición.
    return listado, list(dict.fromkeys(faltantes))


def texto_para_compartir(listado: list[dict]) -> str:
    lineas = ["🎵 Listado", ""]

    for idx, song in enumerate(listado, start=1):
        tono = (song.get("Tono") or "").strip()
        sufijo = f" ({tono})" if tono else ""

        lineas.append(f"{idx}. {song['Cancion']}{sufijo}")

    return "\n".join(lineas)


def texto_catalogo(songs: list[dict]) -> str:
    """Repertorio completo para compartir: solo número y nombre."""
    lineas = ["🎵 Canciones", ""]

    for song in songs:
        lineas.append(f"{song['Numero']}. {song['Cancion']}")

    return "\n".join(lineas)


def filtrar_canciones(
    songs: list[dict],
    search: str | None = None,
    estado: str | None = None
) -> list[dict]:
    """Filtra por estado y por texto (nombre o número), como la vista Equipo."""
    resultado = songs

    if estado:
        resultado = [s for s in resultado if s["Estado"] == estado]

    if search:
        needle = search.strip().lower()

        resultado = [
            s for s in resultado
            if needle in (s.get("Cancion") or "").lower()
            or needle in str(s["Numero"])
        ]

    return resultado
