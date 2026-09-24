from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Stylework Lead Intake"
    environment: str = "local"
    cors_origins: list[str] = ["http://localhost:5173"]


# Cached so settings are parsed once; tests can call get_settings.cache_clear() to reload.
@lru_cache
def get_settings() -> Settings:
    return Settings()
