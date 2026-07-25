"""
Resolves the authenticated user's identity to exactly one FHIR Patient ID.

This is the only place in the codebase that maps a verified username/email
to a Patient resource. The resulting Patient ID is stored in the server-side
session and used automatically for every subsequent clinical data request -
it is never accepted as user input.
"""
from __future__ import annotations

from app.config.settings import get_settings
from app.fhir.client import FHIRClient
from app.utils.errors import PatientIdentityConflictError, PatientNotFoundError
from app.utils.logging import get_logger

logger = get_logger("amakomaya.fhir.patient_resolver")


async def resolve_patient_id(identifier: str) -> str:
    """
    Look up the Patient resource matching the verified identifier
    (preferred_username or email from the JWT).

    Uses a service-account token for this lookup step only - clinical data
    reads always use the patient's own session token, scoped to their
    resolved Patient ID.
    """
    settings = get_settings()
    client = FHIRClient(access_token=settings.fhir_service_token)

    bundle = await client.search("Patient", params={"identifier": identifier})
    entries = bundle.get("entry", [])

    if len(entries) == 0:
        logger.info("patient_not_found")
        raise PatientNotFoundError()

    if len(entries) > 1:
        logger.warning("patient_identity_conflict count=%d", len(entries))
        raise PatientIdentityConflictError()

    patient_resource = entries[0]["resource"]
    return patient_resource["id"]
