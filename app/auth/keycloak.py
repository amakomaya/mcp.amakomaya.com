"""
Keycloak OAuth2 / OpenID Connect helper.

Implements the Authorization Code flow with PKCE. This module never asks
the user for a password - it only redirects to Keycloak's hosted login
page and exchanges the returned authorization code for tokens.
"""
from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.config.settings import get_settings
from app.utils.errors import UnauthorizedError
from app.utils.logging import get_logger

logger = get_logger("amakomaya.auth.keycloak")


@dataclass
class PKCEChallenge:
    verifier: str
    challenge: str
    state: str


def generate_pkce_challenge() -> PKCEChallenge:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    state = secrets.token_urlsafe(24)
    return PKCEChallenge(verifier=verifier, challenge=challenge, state=state)


def build_authorization_url(pkce: PKCEChallenge) -> str:
    settings = get_settings()
    params = {
        "client_id": settings.keycloak_client_id,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": settings.keycloak_redirect_uri,
        "state": pkce.state,
        "code_challenge": pkce.challenge,
        "code_challenge_method": "S256",
    }
    return f"{settings.keycloak_auth_url}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str, verifier: str) -> dict:
    """Exchange an authorization code for access/refresh tokens."""
    settings = get_settings()
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.keycloak_client_id,
        "code": code,
        "redirect_uri": settings.keycloak_redirect_uri,
        "code_verifier": verifier,
    }
    if settings.keycloak_client_secret:
        data["client_secret"] = settings.keycloak_client_secret

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(settings.keycloak_token_url, data=data)

    if response.status_code != 200:
        logger.warning("token_exchange_failed status=%s", response.status_code)
        raise UnauthorizedError("Login failed. Please try signing in again.")

    return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Exchange a refresh token for a new access token."""
    settings = get_settings()
    data = {
        "grant_type": "refresh_token",
        "client_id": settings.keycloak_client_id,
        "refresh_token": refresh_token,
    }
    if settings.keycloak_client_secret:
        data["client_secret"] = settings.keycloak_client_secret

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(settings.keycloak_token_url, data=data)

    if response.status_code != 200:
        logger.info("token_refresh_failed status=%s", response.status_code)
        raise UnauthorizedError("Your session has expired. Please sign in again.")

    return response.json()
