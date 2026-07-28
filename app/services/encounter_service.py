"""Encounter resource lookups."""
from __future__ import annotations

from typing import Any

from app.fhir.client import get_fhir_client
from app.services.base import bundle_summary


async def get_encounter(encounter_id: str) -> dict[str, Any]:
    return await get_fhir_client().read("Encounter", encounter_id)


async def search_encounters(patient_id: str, count: int = 20) -> dict[str, Any]:
    bundle = await get_fhir_client().search(
        "Encounter",
        params={"patient": patient_id, "_sort": "-date", "_count": count},
    )
    return bundle_summary(bundle)
