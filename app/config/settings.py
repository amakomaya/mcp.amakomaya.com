"""
Centralized application configuration.

All configuration is loaded from environment variables (see .env.example).
Nothing in this file should ever contain a real secret - only field
definitions and safe defaults.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- FHIR ---
    fhir_base_url: str
    fhir_timeout: float = 30.0
    fhir_max_retries: int = 3

    # Credentials - all optional. FHIRClient picks whichever is configured:
    # a bearer token takes priority over basic auth, and if neither is set
    # requests are sent unauthenticated.
    fhir_username: str = ""
    fhir_password: str = ""
    fhir_token: str = ""

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Settings are cached - env vars are read once per process."""
    return Settings()
