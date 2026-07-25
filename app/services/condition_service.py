"""Condition (diagnosis) data, scoped to the authenticated patient."""
from __future__ import annotations

from app.services.base import bundle_resources, make_client, patient_reference


async def list_conditions(access_token: str, patient_id: str) -> list[dict]:
    client = make_client(access_token)
    bundle = await client.search(
        "Condition",
        params={"patient": patient_reference(patient_id), "_sort": "-recorded-date", "_count": 20},
    )

    conditions = []
    for resource in bundle_resources(bundle):
        conditions.append({
            "condition": (resource.get("code") or {}).get("text"),
            "clinical_status": ((resource.get("clinicalStatus") or {}).get("coding") or [{}])[0].get("code"),
            "onset": resource.get("onsetDateTime"),
            "recorded_date": resource.get("recordedDate"),
        })
    return conditions
