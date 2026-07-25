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

    # --- Keycloak ---
    keycloak_url: str
    keycloak_realm: str
    keycloak_client_id: str
    keycloak_client_secret: str = ""
    keycloak_redirect_uri: str = "http://localhost:8000/auth/callback"

    # --- FHIR ---
    fhir_base_url: str
    fhir_timeout: int = 30
    fhir_service_token: str = ""

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # --- Session ---
    session_secret_key: str = "change-me-in-production"
    session_ttl_seconds: int = 3600

    @property
    def keycloak_issuer(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"

    @property
    def keycloak_jwks_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/certs"

    @property
    def keycloak_token_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/token"

    @property
    def keycloak_auth_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/auth"


@lru_cache
def get_settings() -> Settings:
    """Settings are cached - env vars are read once per process."""
    return Settings()
