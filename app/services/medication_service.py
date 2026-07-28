"""MedicationRequest resource lookups."""
from __future__ import annotations

from typing import Any

from app.fhir.client import get_fhir_client
from app.services.base import bundle_summary


async def search_medications(patient_id: str, count: int = 20) -> dict[str, Any]:
    bundle = await get_fhir_client().search(
        "MedicationRequest",
        params={"patient": patient_id, "_sort": "-authoredon", "_count": count},
    )
    return bundle_summary(bundle)
