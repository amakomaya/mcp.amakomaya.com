"""
Thin, reusable async HTTP client for the FHIR REST API.

This is the ONLY module in the codebase allowed to make network calls to
the FHIR server. No SQL, no ORM, no direct database access anywhere.

Authentication is selected automatically from configuration (see
app/config/settings.py), in priority order:
  1. Bearer token   (FHIR_TOKEN is set)
  2. Basic auth      (FHIR_USERNAME + FHIR_PASSWORD are set)
  3. No authentication (nothing configured)
"""
from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

import httpx

from app.config.settings import Settings, get_settings
from app.utils.errors import (
    ForbiddenError,
    InternalError,
    NotFoundError,
    TimeoutErrorApp,
    UnauthorizedError,
)
from app.utils.logging import get_logger

logger = get_logger("amakomaya.fhir")

# Server-side errors worth a retry; anything else fails fast.
_RETRYABLE_STATUS_CODES = {502, 503, 504}
_BACKOFF_BASE_SECONDS = 0.5


class FHIRClient:
    """Reusable client for a configured FHIR server."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def read(self, resource_type: str, resource_id: str) -> dict[str, Any]:
        """GET /<resource_type>/<id> and return the raw FHIR resource."""
        return await self._request("GET", f"/{resource_type}/{resource_id}")

    async def search(
        self, resource_type: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """GET /<resource_type>?<params> and return the raw FHIR Bundle."""
        return await self._request("GET", f"/{resource_type}", params=params)

    async def capabilities(self) -> dict[str, Any]:
        """GET /metadata, the server's FHIR CapabilityStatement."""
        return await self._request("GET", "/metadata")

    async def raw_get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET an arbitrary path relative to the FHIR base URL, for debugging."""
        if not path.startswith("/"):
            path = f"/{path}"
        return await self._request("GET", path, params=params)

    def _basic_auth(self) -> httpx.BasicAuth | None:
        if self._settings.fhir_token:
            return None
        if self._settings.fhir_username and self._settings.fhir_password:
            return httpx.BasicAuth(self._settings.fhir_username, self._settings.fhir_password)
        return None

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/fhir+json"}
        if self._settings.fhir_token:
            headers["Authorization"] = f"Bearer {self._settings.fhir_token}"
        return headers

    async def _request(
        self, method: str, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{self._settings.fhir_base_url.rstrip('/')}{path}"
        max_attempts = max(1, self._settings.fhir_max_retries)

        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self._settings.fhir_timeout,
                    auth=self._basic_auth(),
                ) as client:
                    response = await client.request(
                        method, url, headers=self._headers(), params=params
                    )
            except httpx.TimeoutException:
                logger.warning("fhir_timeout path=%s attempt=%d/%d", path, attempt, max_attempts)
                if attempt == max_attempts:
                    raise TimeoutErrorApp()
                await asyncio.sleep(_BACKOFF_BASE_SECONDS * attempt)
                continue
            except httpx.HTTPError as exc:
                logger.warning(
                    "fhir_connection_error path=%s attempt=%d/%d error=%s",
                    path, attempt, max_attempts, exc,
                )
                if attempt == max_attempts:
                    raise InternalError()
                await asyncio.sleep(_BACKOFF_BASE_SECONDS * attempt)
                continue

            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < max_attempts:
                logger.warning(
                    "fhir_retryable_status status=%s path=%s attempt=%d/%d",
                    response.status_code, path, attempt, max_attempts,
                )
                await asyncio.sleep(_BACKOFF_BASE_SECONDS * attempt)
                continue

            return self._handle_response(response, path)

        # Unreachable: the loop above always returns or raises.
        raise InternalError()

    @staticmethod
    def _handle_response(response: httpx.Response, path: str) -> dict[str, Any]:
        if response.status_code == 200:
            return response.json()
        if response.status_code == 401:
            logger.warning("fhir_unauthorized path=%s", path)
            raise UnauthorizedError("The FHIR server rejected the configured credentials.")
        if response.status_code == 403:
            logger.warning("fhir_forbidden path=%s", path)
            raise ForbiddenError()
        if response.status_code == 404:
            raise NotFoundError()
        if response.status_code == 408:
            raise TimeoutErrorApp()

        logger.error("fhir_error status=%s path=%s", response.status_code, path)
        raise InternalError()


@lru_cache
def get_fhir_client() -> FHIRClient:
    """Process-wide FHIR client, built from cached settings."""
    return FHIRClient()
