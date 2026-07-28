"""MCP server health and FHIR server connectivity checks."""
from __future__ import annotations

from typing import Any

from app.config.settings import get_settings
from app.fhir.client import get_fhir_client
from app.utils.errors import AppError


async def check_server_status() -> dict[str, Any]:
    settings = get_settings()
    status: dict[str, Any] = {
        "mcp_server": "ok",
        "fhir_base_url": settings.fhir_base_url,
    }

    try:
        capability = await get_fhir_client().capabilities()
    except AppError as exc:
        status["fhir_server"] = "unreachable"
        status["error"] = exc.friendly_message
        return status

    software = capability.get("software") or {}
    status["fhir_server"] = "reachable"
    status["fhir_version"] = capability.get("fhirVersion")
    status["fhir_software"] = software.get("name")
    return status
