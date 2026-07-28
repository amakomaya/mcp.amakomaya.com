"""Patient resource lookups."""
from __future__ import annotations

from typing import Any

from app.fhir.client import get_fhir_client
from app.services.base import bundle_summary


async def get_patient(patient_id: str) -> dict[str, Any]:
    return await get_fhir_client().read("Patient", patient_id)


async def search_patients(
    *,
    family: str | None = None,
    given: str | None = None,
    identifier: str | None = None,
    birthdate: str | None = None,
    count: int = 20,
) -> dict[str, Any]:
    params: dict[str, Any] = {"_count": count}
    if family:
        params["family"] = family
    if given:
        params["given"] = given
    if identifier:
        params["identifier"] = identifier
    if birthdate:
        params["birthdate"] = birthdate

    bundle = await get_fhir_client().search("Patient", params=params)
    return bundle_summary(bundle)
