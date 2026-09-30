from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

EstadoValor = Literal["OK", "APRENDIENDO"]
TipoValor = Literal["Lenta", "Movida"]


def _blank_to_none(value):
    if isinstance(value, str) and not value.strip():
        return None

    return value


class SongBase(BaseModel):
    Cancion: str = Field(min_length=1, max_length=300)
    Notas_Piano: str | None = None
    Notas_Guitarra: str | None = None
    Letra: str | None = None
    Video_Bateria: str | None = None
    Tono: str | None = None
    Estado: EstadoValor = "APRENDIENDO"
    Tipo: TipoValor = "Lenta"
    Audio: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _normalize_blanks(cls, value):
        return _blank_to_none(value)


class SongCreate(SongBase):
    """Alta de canción. El Numero lo asigna el backend."""


class SongUpdate(BaseModel):
    """Actualización parcial: solo se tocan los campos presentes."""

    Cancion: str | None = Field(default=None, min_length=1, max_length=300)
    Notas_Piano: str | None = None
    Notas_Guitarra: str | None = None
    Letra: str | None = None
    Video_Bateria: str | None = None
    Tono: str | None = None
    Estado: EstadoValor | None = None
    Tipo: TipoValor | None = None
    Audio: str | None = None


class Song(SongBase):
    Numero: int


class SetlistPublish(BaseModel):
    """Listado a publicar: números en orden, se admiten repetidos."""

    numeros: list[int] = Field(min_length=1)


class SetlistResponse(BaseModel):
    canciones: list[Song] = Field(default_factory=list)

    # Números que estaban en el listado pero ya no existen en la base.
    faltantes: list[int] = Field(default_factory=list)

    publicado: datetime | None = None
    texto_compartir: str = ""
