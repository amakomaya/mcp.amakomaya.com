"""
JWT validation against Keycloak's JWKS.

Validates:
  - signature (against Keycloak's public keys)
  - issuer
  - audience
  - expiration

Never accepts an unsigned or "none" algorithm token.
"""
from __future__ import annotations

import time

import httpx
from jose import jwt
from jose.exceptions import JOSEError

from app.auth.models import TokenClaims
from app.config.settings import get_settings
from app.utils.errors import UnauthorizedError
from app.utils.logging import get_logger

logger = get_logger("amakomaya.auth")

_ALLOWED_ALGORITHMS = ["RS256"]


class JWKSCache:
    """Small in-memory cache for Keycloak's JSON Web Key Set."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._keys: dict | None = None
        self._fetched_at: float = 0.0

    async def get_keys(self) -> dict:
        now = time.time()
        if self._keys is None or (now - self._fetched_at) > self._ttl:
            settings = get_settings()
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(settings.keycloak_jwks_url)
                response.raise_for_status()
                self._keys = response.json()
                self._fetched_at = now
        return self._keys


_jwks_cache = JWKSCache()


async def validate_access_token(token: str) -> TokenClaims:
    """
    Validate a JWT access token issued by Keycloak.

    Raises UnauthorizedError on any validation failure. Never logs the
    token itself.
    """
    settings = get_settings()

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JOSEError:
        raise UnauthorizedError("Your session is invalid. Please sign in again.")

    kid = unverified_header.get("kid")
    if not kid:
        raise UnauthorizedError("Your session is invalid. Please sign in again.")

    jwks = await _jwks_cache.get_keys()
    signing_key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if signing_key is None:
        raise UnauthorizedError("Your session could not be verified. Please sign in again.")

    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=_ALLOWED_ALGORITHMS,
            audience=settings.keycloak_client_id,
            issuer=settings.keycloak_issuer,
            options={"verify_aud": True, "verify_iss": True, "verify_exp": True},
        )
    except JOSEError as exc:
        logger.warning("jwt_validation_failed reason=%s", type(exc).__name__)
        raise UnauthorizedError("Your session has expired. Please sign in again.")

    return TokenClaims(**payload)
