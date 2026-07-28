"""
MCP tool definitions.

Every tool follows the same pattern:
  1. Call the corresponding service, which talks to the FHIR server through
     app.fhir.client.FHIRClient.
  2. Return the result - or a friendly error message.

NOTE: This build has no authentication or identity management (temporary
development milestone - see README.md). Every tool that touches clinical
data takes an explicit FHIR resource id or patient id from the caller.
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.config.settings import get_settings
from app.services import (
    encounter_service,
    medication_service,
    observation_service,
    patient_service,
    raw_service,
    status_service,
)
from app.utils.errors import AppError
from app.utils.logging import log_tool_call

_LOCAL_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
_LOCAL_ORIGINS = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]


def _build_transport_security() -> TransportSecuritySettings:
    """
    The MCP SDK's DNS-rebinding protection rejects any Host/Origin header
    not on an explicit allowlist. It auto-allows localhost, but a public
    deployment needs its real hostname(s) added via MCP_ALLOWED_HOSTS -
    otherwise every request 421s with "Invalid Host header".
    """
    extra_hosts = [h.strip() for h in get_settings().mcp_allowed_hosts.split(",") if h.strip()]
    allowed_hosts = [*_LOCAL_HOSTS, *extra_hosts, *(f"{h}:*" for h in extra_hosts)]
    allowed_origins = [
        *_LOCAL_ORIGINS,
        *(f"https://{h}" for h in extra_hosts),
        *(f"http://{h}" for h in extra_hosts),
    ]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


mcp = FastMCP("amakomaya", transport_security=_build_transport_security())


async def _run(tool_name: str, coro):
    """Shared execution wrapper: logging + friendly error handling."""
    with log_tool_call(tool_name):
        try:
            return await coro
        except AppError as exc:
            return {"error": exc.friendly_message}


@mcp.tool()
async def server_status() -> dict:
    """Check MCP server health and FHIR server connectivity, including the FHIR version if available."""
    return await _run("server_status", status_service.check_server_status())


@mcp.tool()
async def get_patient(patient_id: str) -> dict:
    """Retrieve a Patient resource by its FHIR id."""
    return await _run("get_patient", patient_service.get_patient(patient_id))


@mcp.tool()
async def search_patients(
    family: str | None = None,
    given: str | None = None,
    identifier: str | None = None,
    birthdate: str | None = None,
    count: int = 20,
) -> dict:
    """Search for patients by family name, given name, identifier, or birth date (YYYY-MM-DD)."""
    return await _run(
        "search_patients",
        patient_service.search_patients(
            family=family,
            given=given,
            identifier=identifier,
            birthdate=birthdate,
            count=count,
        ),
    )


@mcp.tool()
async def get_observation(observation_id: str) -> dict:
    """Retrieve an Observation resource by its FHIR id."""
    return await _run("get_observation", observation_service.get_observation(observation_id))


@mcp.tool()
async def search_observations(patient_id: str, count: int = 20) -> dict:
    """Search Observation resources for a given patient FHIR id."""
    return await _run(
        "search_observations",
        observation_service.search_observations(patient_id, count=count),
    )


@mcp.tool()
async def get_encounter(encounter_id: str) -> dict:
    """Retrieve an Encounter resource by its FHIR id."""
    return await _run("get_encounter", encounter_service.get_encounter(encounter_id))


@mcp.tool()
async def search_encounters(patient_id: str, count: int = 20) -> dict:
    """Search Encounter resources for a given patient FHIR id."""
    return await _run(
        "search_encounters",
        encounter_service.search_encounters(patient_id, count=count),
    )


@mcp.tool()
async def search_medications(patient_id: str, count: int = 20) -> dict:
    """Search MedicationRequest resources for a given patient FHIR id."""
    return await _run(
        "search_medications",
        medication_service.search_medications(patient_id, count=count),
    )


@mcp.tool()
async def raw_fhir(path: str, params: dict[str, Any] | None = None) -> dict:
    """
    Execute a raw GET request against any FHIR endpoint, for debugging.

    `path` is relative to the configured FHIR base URL, e.g. "Patient" or
    "Patient/123/_history". `params` are FHIR search/query parameters.
    """
    return await _run("raw_fhir", raw_service.execute_raw_get(path, params=params))
