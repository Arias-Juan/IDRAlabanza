"""Toda la I/O contra BigQuery.

Se usa DML parametrizado (nunca interpolación de strings en el SQL) tanto
para leer como para escribir. Las filas insertadas por DML no pasan por el
streaming buffer, así que se pueden borrar o actualizar enseguida.
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any

from google.cloud import bigquery

from .config import get_settings

logger = logging.getLogger(__name__)

SONG_FIELDS = (
    "Cancion",
    "Notas_Piano",
    "Notas_Guitarra",
    "Letra",
    "Video_Bateria",
    "Tono",
    "Estado",
    "Tipo",
    "Audio"
)

_client: bigquery.Client | None = None
_client_lock = threading.Lock()


def get_client() -> bigquery.Client:
    """Cliente BigQuery vía ADC.

    En Cloud Run usa la service account del servicio; en local, las
    credenciales de `gcloud auth application-default login`.
    """
    global _client

    if _client is None:
        with _client_lock:
            if _client is None:
                settings = get_settings()

                _client = bigquery.Client(project=settings.project_id)

    return _client


class _TTLCache:
    """Caché en proceso, equivalente al `st.cache_data(ttl=...)` original.

    Cada instancia de Cloud Run tiene la suya: por eso los TTL son cortos.
    """

    def __init__(self, ttl: float):
        self._ttl = ttl
        self._lock = threading.Lock()
        self._value: Any = None
        self._expires_at = 0.0

    def get(self):
        with self._lock:
            if self._value is not None and time.monotonic() < self._expires_at:
                return self._value

        return None

    def set(self, value):
        with self._lock:
            self._value = value
            self._expires_at = time.monotonic() + self._ttl

    def clear(self):
        with self._lock:
            self._value = None
            self._expires_at = 0.0


_settings = get_settings()

_songs_cache = _TTLCache(_settings.songs_cache_ttl)
_setlist_cache = _TTLCache(_settings.setlist_cache_ttl)


def _run(sql: str, params: list | None = None) -> list[dict]:
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])

    rows = get_client().query(sql, job_config=job_config).result()

    return [dict(row.items()) for row in rows]


def _normalize_song(row: dict) -> dict:
    song = {"Numero": int(row["Numero"])}

    for field in SONG_FIELDS:
        value = row.get(field)

        song[field] = None if value is None or value == "" else value

    # Estado y Tipo no aceptan null del lado del modelo: si la fila vieja
    # los tiene vacíos, se cae al mismo default que usaba el formulario.
    song["Estado"] = song["Estado"] or "APRENDIENDO"
    song["Tipo"] = song["Tipo"] or "Lenta"

    return song


def list_songs(use_cache: bool = True) -> list[dict]:
    if use_cache:
        cached = _songs_cache.get()

        if cached is not None:
            return cached

    settings = get_settings()

    rows = _run(
        f"SELECT * FROM `{settings.table_id}` ORDER BY Numero"
    )

    songs = [_normalize_song(row) for row in rows]

    _songs_cache.set(songs)

    return songs


def get_song(numero: int) -> dict | None:
    for song in list_songs():
        if song["Numero"] == numero:
            return song

    return None


def insert_song(data: dict) -> dict:
    """Inserta una canción asignando `Numero = MAX(Numero) + 1`.

    El cálculo del próximo número y el INSERT van en un mismo script para
    que dos altas simultáneas no se pisen.
    """
    settings = get_settings()

    columns = ", ".join(SONG_FIELDS)
    placeholders = ", ".join(f"@{field}" for field in SONG_FIELDS)

    sql = f"""
        DECLARE next_num INT64;

        SET next_num = (
            SELECT COALESCE(MAX(Numero), 0) + 1
            FROM `{settings.table_id}`
        );

        INSERT INTO `{settings.table_id}` (Numero, {columns})
        VALUES (next_num, {placeholders});

        SELECT next_num AS Numero;
    """

    params = [
        bigquery.ScalarQueryParameter(field, "STRING", data.get(field))
        for field in SONG_FIELDS
    ]

    rows = _run(sql, params)

    _songs_cache.clear()

    numero = int(rows[0]["Numero"])

    return {"Numero": numero, **{f: data.get(f) for f in SONG_FIELDS}}


def update_song(numero: int, changes: dict) -> bool:
    """Actualiza solo los campos presentes. False si el N° no existe."""
    if not changes:
        return get_song(numero) is not None

    settings = get_settings()

    fields = [f for f in SONG_FIELDS if f in changes]

    assignments = ", ".join(f"{field} = @{field}" for field in fields)

    params: list = [
        bigquery.ScalarQueryParameter(field, "STRING", changes[field])
        for field in fields
    ]

    params.append(
        bigquery.ScalarQueryParameter("numero", "INT64", numero)
    )

    job_config = bigquery.QueryJobConfig(query_parameters=params)

    job = get_client().query(
        f"""
            UPDATE `{settings.table_id}`
            SET {assignments}
            WHERE Numero = @numero
        """,
        job_config=job_config
    )

    job.result()

    _songs_cache.clear()

    return bool(job.num_dml_affected_rows)


def delete_song(numero: int) -> bool:
    settings = get_settings()

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("numero", "INT64", numero)
        ]
    )

    job = get_client().query(
        f"DELETE FROM `{settings.table_id}` WHERE Numero = @numero",
        job_config=job_config
    )

    job.result()

    _songs_cache.clear()

    return bool(job.num_dml_affected_rows)


def get_setlist(use_cache: bool = True) -> list[dict]:
    """Listado vigente (publicado dentro de la ventana de días)."""
    if use_cache:
        cached = _setlist_cache.get()

        if cached is not None:
            return cached

    settings = get_settings()

    rows = _run(
        f"""
            SELECT Orden, Numero, Fecha_Creacion
            FROM `{settings.setlist_table_id}`
            WHERE Fecha_Creacion >= TIMESTAMP_SUB(
                CURRENT_TIMESTAMP(),
                INTERVAL @dias DAY
            )
            ORDER BY Orden
        """,
        [
            bigquery.ScalarQueryParameter(
                "dias",
                "INT64",
                settings.setlist_ttl_days
            )
        ]
    )

    items = [
        {
            "Orden": int(row["Orden"]),
            "Numero": int(row["Numero"]),
            "Fecha_Creacion": row["Fecha_Creacion"]
        }
        for row in rows
    ]

    _setlist_cache.set(items)

    return items


def replace_setlist(numeros: list[int]) -> datetime:
    """Reemplaza el listado publicado. Devuelve la fecha de publicación."""
    settings = get_settings()

    clear_setlist()

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("numeros", "INT64", numeros)
        ]
    )

    get_client().query(
        f"""
            INSERT INTO `{settings.setlist_table_id}`
                (Orden, Numero, Fecha_Creacion)
            SELECT
                offset + 1,
                numero,
                CURRENT_TIMESTAMP()
            FROM UNNEST(@numeros) AS numero WITH OFFSET AS offset
        """,
        job_config=job_config
    ).result()

    _setlist_cache.clear()

    publicado = get_setlist(use_cache=False)

    return publicado[0]["Fecha_Creacion"] if publicado else None


def clear_setlist() -> None:
    settings = get_settings()

    get_client().query(
        f"DELETE FROM `{settings.setlist_table_id}` WHERE TRUE"
    ).result()

    _setlist_cache.clear()
