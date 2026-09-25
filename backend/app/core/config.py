from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Stylework Lead Intake"
    environment: str = "local"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    database_url: str = "postgresql+psycopg://lead_intake:lead_intake@localhost:5432/lead_intake"

    # Used by the Meta webhook (signature verification and subscribe handshake).
    meta_app_secret: str = ""
    meta_verify_token: str = ""

    # Railway and most hosts hand out postgres:// or postgresql:// URLs. SQLAlchemy would pick
    # the psycopg2 driver for those, so pin the psycopg 3 driver explicitly.
    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value.removeprefix(prefix)
        return value

    # Fail fast at startup instead of running a production webhook that rejects every delivery
    # (or, worse, a misconfiguration nobody notices). Locally the values may be empty; the
    # webhook then simply rejects all requests.
    @model_validator(mode="after")
    def require_webhook_secrets_in_production(self) -> "Settings":
        if self.environment == "production":
            missing = [
                name
                for name, value in (
                    ("META_APP_SECRET", self.meta_app_secret),
                    ("META_VERIFY_TOKEN", self.meta_verify_token),
                )
                if not value
            ]
            if missing:
                raise ValueError(f"{', '.join(missing)} must be set when ENVIRONMENT=production")
        return self


# Cached so settings are parsed once; tests can call get_settings.cache_clear() to reload.
@lru_cache
def get_settings() -> Settings:
    return Settings()
