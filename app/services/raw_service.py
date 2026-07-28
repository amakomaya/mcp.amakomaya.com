"""Raw, unmapped access to the FHIR REST API - for debugging only."""
from __future__ import annotations

from typing import Any

from app.fhir.client import get_fhir_client


async def execute_raw_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return await get_fhir_client().raw_get(path, params=params)
