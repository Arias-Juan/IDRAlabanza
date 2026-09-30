from functools import cached_property, lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída del entorno (o de un .env local)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    project_id: str | None = Field(
        default=None,
        description="Proyecto GCP. Si es None se usa el del ADC."
    )

    table_id: str = "asistente-personal-unico.alabanza.canciones"
    setlist_table_id: str = "asistente-personal-unico.alabanza.set_lista"

    # Días que dura publicado un listado, igual que la app Streamlit.
    setlist_ttl_days: int = 7

    # Caché en proceso. El de canciones puede ser largo; el del listado va
    # corto porque el equipo tiene que ver un listado recién publicado.
    songs_cache_ttl: int = 600
    setlist_cache_ttl: int = 60

    # Coma-separadas en el entorno (API_KEYS). Se declara como str porque
    # pydantic-settings intentaría parsear un list[str] como JSON.
    # Sin ninguna key, la escritura queda deshabilitada.
    api_keys_raw: str = Field(default="", alias="API_KEYS")

    @cached_property
    def api_keys(self) -> list[str]:
        return [k.strip() for k in self.api_keys_raw.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
