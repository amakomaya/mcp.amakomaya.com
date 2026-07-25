"""Immunization data, scoped to the authenticated patient."""
from __future__ import annotations

from app.services.base import bundle_resources, make_client, patient_reference


async def list_immunizations(access_token: str, patient_id: str) -> list[dict]:
    client = make_client(access_token)
    bundle = await client.search(
        "Immunization",
        params={"patient": patient_reference(patient_id), "_sort": "-date", "_count": 20},
    )

    immunizations = []
    for resource in bundle_resources(bundle):
        immunizations.append({
            "vaccine": (resource.get("vaccineCode") or {}).get("text"),
            "status": resource.get("status"),
            "occurrence_date": resource.get("occurrenceDateTime"),
        })
    return immunizations
