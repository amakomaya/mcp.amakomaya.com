"""
MCP tool definitions.

Every tool follows the same pattern:
  1. Get the current authenticated session (patient_id + access_token).
  2. Call the corresponding service.
  3. Return a simple, friendly result - or a friendly error message.

Tools never accept a patient id or any identifier from the caller. The
identity used is always the one resolved from the signed-in user's own
session - there is no parameter that could be used to request someone
else's data.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.middleware.auth_middleware import get_current_session
from app.services import (
    appointment_service,
    condition_service,
    document_service,
    immunization_service,
    medication_service,
    observation_service,
    patient_service,
    summary_service,
)
from app.utils.errors import AppError
from app.utils.logging import log_tool_call

mcp = FastMCP("amakomaya")


async def _run(tool_name: str, coro):
    """Shared execution wrapper: logging + friendly error handling."""
    with log_tool_call(tool_name):
        try:
            return await coro
        except AppError as exc:
            return {"error": exc.friendly_message}


@mcp.tool()
async def get_my_profile() -> dict:
    """Get the signed-in user's own basic profile (name, gender, birth date, phone)."""
    session = get_current_session()
    return await _run(
        "get_my_profile",
        patient_service.get_profile(session.access_token, session.patient_id),
    )


@mcp.tool()
async def my_appointments() -> dict:
    """List the signed-in user's own appointments (past and upcoming)."""
    session = get_current_session()
    result = await _run(
        "my_appointments",
        appointment_service.list_appointments(session.access_token, session.patient_id),
    )
    return {"appointments": result} if isinstance(result, list) else result


@mcp.tool()
async def my_medications() -> dict:
    """List the signed-in user's own medications."""
    session = get_current_session()
    result = await _run(
        "my_medications",
        medication_service.list_medications(session.access_token, session.patient_id),
    )
    return {"medications": result} if isinstance(result, list) else result


@mcp.tool()
async def my_conditions() -> dict:
    """List the signed-in user's own documented health conditions."""
    session = get_current_session()
    result = await _run(
        "my_conditions",
        condition_service.list_conditions(session.access_token, session.patient_id),
    )
    return {"conditions": result} if isinstance(result, list) else result


@mcp.tool()
async def my_observations() -> dict:
    """
    List the signed-in user's own recorded observations (vitals / lab
    results), as documented. This tool does not interpret or diagnose.
    """
    session = get_current_session()
    result = await _run(
        "my_observations",
        observation_service.list_observations(session.access_token, session.patient_id),
    )
    return {"observations": result} if isinstance(result, list) else result


@mcp.tool()
async def my_immunizations() -> dict:
    """List the signed-in user's own immunization history."""
    session = get_current_session()
    result = await _run(
        "my_immunizations",
        immunization_service.list_immunizations(session.access_token, session.patient_id),
    )
    return {"immunizations": result} if isinstance(result, list) else result


@mcp.tool()
async def my_documents() -> dict:
    """List the signed-in user's own clinical documents (letters, summaries)."""
    session = get_current_session()
    result = await _run(
        "my_documents",
        document_service.list_documents(session.access_token, session.patient_id),
    )
    return {"documents": result} if isinstance(result, list) else result


@mcp.tool()
async def my_clinical_summary() -> dict:
    """Get a combined snapshot: profile, upcoming appointments, active
    medications and conditions, recent observations, and immunizations."""
    session = get_current_session()
    return await _run(
        "my_clinical_summary",
        summary_service.get_clinical_summary(session.access_token, session.patient_id),
    )


@mcp.tool()
async def server_status() -> dict:
    """Check whether the Amakomaya MCP server is running normally."""
    return {"status": "ok", "service": "amakomaya-mcp"}
