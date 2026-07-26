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

    # --- Auth toggle (temporary) ---
    # TODO(auth): this flag exists only to let Claude Desktop / MCP
    # Inspector connect and exercise the MCP protocol without Keycloak in
    # the loop. Restore auth_enabled defaulting to True everywhere and
    # remove AUTH_DISABLED_PATIENT_ID once the protocol wiring is verified.
    # See app/middleware/auth_middleware.py for the bypass this gates.
    auth_enabled: bool = True
    # FHIR Patient resource id (not an email/username - no lookup happens
    # in bypass mode) that every request is treated as, while auth is off.
    auth_disabled_patient_id: str = ""
    # Used only to decide whether AUTH_ENABLED=false is allowed to boot.
    environment: str = "development"

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
