"""
Observation (vitals / labs) data, scoped to the authenticated patient.

NOTE: this service returns the documented values only. It never
interprets, diagnoses, or comments on clinical significance - that
judgement belongs to the care team, not to this tool.
"""
from __future__ import annotations

from app.services.base import bundle_resources, make_client, patient_reference


async def list_observations(access_token: str, patient_id: str) -> list[dict]:
    client = make_client(access_token)
    bundle = await client.search(
        "Observation",
        params={"patient": patient_reference(patient_id), "_sort": "-date", "_count": 20},
    )

    observations = []
    for resource in bundle_resources(bundle):
        value = resource.get("valueQuantity")
        value_text = f"{value['value']} {value.get('unit', '')}".strip() if value else resource.get("valueString")

        observations.append({
            "observation": (resource.get("code") or {}).get("text"),
            "value": value_text,
            "effective_date": resource.get("effectiveDateTime"),
            "status": resource.get("status"),
        })
    return observations
