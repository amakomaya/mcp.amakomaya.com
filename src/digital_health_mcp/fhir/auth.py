"""Keycloak login and access-token validation.

`login_with_password` performs a Keycloak Direct Access Grant (OAuth2
Resource Owner Password Credentials) login with a phone-number username and
password, then verifies the resulting access token's signature against the
realm's published JWKS, its expiry, and its issuer before trusting its
`preferred_username` claim. This is used only to establish who is calling --
the token is never forwarded to the FHIR server. FHIR requests continue to
authenticate as the service account configured via FHIR_TOKEN or
FHIR_USERNAME/FHIR_PASSWORD (see ../config.py).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import httpx
import jwt
from jwt import PyJWKClient


class ConfigError(RuntimeError):
    """Raised when required Keycloak configuration is missing."""


class KeycloakError(RuntimeError):
    """Raised when login fails or the access token is malformed/unverifiable."""


@dataclass(frozen=True)
class Settings:
    issuer: str
    jwks_url: str
    token_url: str
    client_id: str
    client_secret: str | None
    audience: str | None
    verify_ssl: bool


def load_settings() -> Settings:
    issuer = os.environ.get("KEYCLOAK_ISSUER", "").strip().rstrip("/")
    if not issuer:
        raise ConfigError(
            "KEYCLOAK_ISSUER is not set. Point it at your realm, e.g. "
            "https://keycloak.example.com/realms/amakomaya"
        )
    client_id = os.environ.get("KEYCLOAK_CLIENT_ID", "").strip()
    if not client_id:
        raise ConfigError(
            "KEYCLOAK_CLIENT_ID is not set. This must be a client in your "
            "realm with Direct Access Grants enabled."
        )
    jwks_url = (
        os.environ.get("KEYCLOAK_JWKS_URL", "").strip()
        or f"{issuer}/protocol/openid-connect/certs"
    )
    token_url = (
        os.environ.get("KEYCLOAK_TOKEN_URL", "").strip()
        or f"{issuer}/protocol/openid-connect/token"
    )
    client_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET", "").strip() or None
    audience = os.environ.get("KEYCLOAK_AUDIENCE", "").strip() or None
    verify_ssl = os.environ.get("KEYCLOAK_VERIFY_SSL", "true").strip().lower() not in (
        "false",
        "0",
        "no",
    )
    return Settings(
        issuer=issuer,
        jwks_url=jwks_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        audience=audience,
        verify_ssl=verify_ssl,
    )


@lru_cache(maxsize=1)
def _jwk_client(jwks_url: str) -> PyJWKClient:
    """Cached JWKS client so we don't refetch Keycloak's signing keys on
    every call. PyJWKClient itself caches individual keys by kid."""
    return PyJWKClient(jwks_url)


def extract_preferred_username(access_token: str) -> str:
    """Validate a Keycloak access token and return its `preferred_username`.

    Verifies the token's signature against the realm's JWKS, its expiry (if
    present), and its issuer. Raises KeycloakError with a clear, actionable
    message if the token is missing, expired, malformed, or fails
    verification for any other reason.
    """
    if not access_token or not access_token.strip():
        raise KeycloakError("No access token provided.")

    settings = load_settings()
    try:
        signing_key = _jwk_client(settings.jwks_url).get_signing_key_from_jwt(
            access_token
        )
        claims = jwt.decode(
            access_token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.issuer,
            audience=settings.audience,
            options={"verify_aud": settings.audience is not None},
        )
    except jwt.PyJWTError as exc:
        raise KeycloakError(f"Access token validation failed: {exc}") from exc
    except Exception as exc:  # JWKS unreachable, malformed response, etc.
        raise KeycloakError(f"Could not validate token against Keycloak: {exc}") from exc

    username = claims.get("preferred_username")
    if not username:
        raise KeycloakError("Token is valid but has no 'preferred_username' claim.")
    return username


def login_with_password(username: str, password: str) -> str:
    """Log in to Keycloak with a username (phone number) and password, and
    return the verified `preferred_username` from the resulting token.

    Uses the OAuth2 Resource Owner Password Credentials grant (Keycloak
    calls this "Direct Access Grants"), which must be enabled on
    KEYCLOAK_CLIENT_ID. Raises KeycloakError with a generic "incorrect"
    message on bad credentials (never echoing Keycloak's internal error
    detail back to the caller), and a more specific message for
    configuration or connectivity failures.
    """
    if not username or not username.strip() or not password:
        raise KeycloakError("Username and password are required.")

    settings = load_settings()
    data = {
        "grant_type": "password",
        "client_id": settings.client_id,
        "username": username,
        "password": password,
        "scope": "openid",
    }
    if settings.client_secret:
        data["client_secret"] = settings.client_secret

    try:
        r = httpx.post(
            settings.token_url, data=data, timeout=15, verify=settings.verify_ssl
        )
    except httpx.RequestError as exc:
        raise KeycloakError(f"Could not reach Keycloak: {exc}") from exc

    if r.status_code != 200:
        raise KeycloakError("Incorrect phone number or password.")

    access_token = r.json().get("access_token")
    if not access_token:
        raise KeycloakError("Keycloak did not return an access token.")

    return extract_preferred_username(access_token)
