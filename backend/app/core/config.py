from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la app, cargada desde variables de entorno (.env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    database_url: str = "sqlite:///./local.db"
    app_timezone: str = "Europe/Madrid"
    cors_origins: str = "http://localhost:5173"

    # Firma de los JWT. En producción DEBE venir de un secreto (Secret Manager);
    # el default solo existe para que el arranque local sin .env no explote.
    secret_key: str = "dev-secret-change-me"
    # PWA de uso personal: tokens largos para no tener que reloguear en el gym.
    access_token_days: int = 30

    # Defaults de la alarma antisedentarismo. El usuario puede sobreescribirlos
    # en tiempo de ejecución vía /api/v1/settings, pero estos son el punto de partida
    # que se siembra en la tabla `app_settings`.
    break_interval_minutes: int = 45
    break_window_start: str = "08:30"
    break_window_end: str = "15:00"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
