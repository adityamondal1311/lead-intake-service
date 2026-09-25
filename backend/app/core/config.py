import re
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# A browser Origin header: scheme + host (+ port), no path and no trailing slash.
_ORIGIN = re.compile(r"^https?://[^/\s]+$")


class Settings(BaseSettings):
    """Application configuration, read from environment variables (and backend/.env locally).

    Every value is validated at startup, so a misconfiguration stops the app instead of letting
    it run with unexpected behaviour.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Stylework Lead Intake"
    # Exact values only: a typo such as "prod" must fail rather than silently skip the
    # production checks below.
    environment: Literal["local", "test", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    # A JSON list in the environment, e.g. CORS_ORIGINS=["https://app.example.com"].
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

    # Browsers send Origin without a path or trailing slash, and CORS matches it exactly. An
    # entry like "https://app.example.com/" would never match, blocking every browser request
    # with no server-side error, so reject it here.
    @field_validator("cors_origins")
    @classmethod
    def origins_are_exact(cls, origins: list[str]) -> list[str]:
        invalid = [origin for origin in origins if not _ORIGIN.fullmatch(origin)]
        if invalid:
            raise ValueError(
                f"invalid origin(s) {invalid}: use scheme://host[:port] with no path or trailing "
                'slash, e.g. ["https://app.example.com"]'
            )
        return origins

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
