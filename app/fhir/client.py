"""
Thin async HTTP client for the FHIR REST API.

This is the ONLY module in the codebase allowed to make network calls to
the FHIR server. No SQL, no ORM, no direct database access anywhere.
"""
from __future__ import annotations

import httpx

from app.config.settings import get_settings
from app.utils.errors import (
    ForbiddenError,
    InternalError,
    NotFoundError,
    TimeoutErrorApp,
    UnauthorizedError,
)
from app.utils.logging import get_logger

logger = get_logger("amakomaya.fhir")


class FHIRClient:
    """Bearer-authenticated client for a single FHIR request."""

    def __init__(self, access_token: str) -> None:
        self._settings = get_settings()
        self._access_token = access_token

    async def search(self, resource_type: str, params: dict | None = None) -> dict:
        """GET /<resource_type>?<params> and return the raw FHIR Bundle."""
        return await self._request("GET", f"/{resource_type}", params=params)

    async def read(self, resource_type: str, resource_id: str) -> dict:
        """GET /<resource_type>/<id> and return the raw FHIR resource."""
        return await self._request("GET", f"/{resource_type}/{resource_id}")

    async def _request(self, method: str, path: str, params: dict | None = None) -> dict:
        url = f"{self._settings.fhir_base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/fhir+json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._settings.fhir_timeout) as client:
                response = await client.request(method, url, headers=headers, params=params)
        except httpx.TimeoutException:
            logger.warning("fhir_timeout path=%s", path)
            raise TimeoutErrorApp()
        except httpx.HTTPError:
            logger.warning("fhir_connection_error path=%s", path)
            raise InternalError()

        return self._handle_response(response, path)

    @staticmethod
    def _handle_response(response: httpx.Response, path: str) -> dict:
        if response.status_code == 200:
            return response.json()
        if response.status_code == 401:
            logger.warning("fhir_unauthorized path=%s", path)
            raise UnauthorizedError()
        if response.status_code == 403:
            logger.warning("fhir_forbidden path=%s", path)
            raise ForbiddenError()
        if response.status_code == 404:
            raise NotFoundError()
        if response.status_code == 408:
            raise TimeoutErrorApp()

        logger.error("fhir_error status=%s path=%s", response.status_code, path)
        raise InternalError()
