"""DocumentReference data (e.g. discharge summaries, referral letters)."""
from __future__ import annotations

from app.services.base import bundle_resources, make_client, patient_reference


async def list_documents(access_token: str, patient_id: str) -> list[dict]:
    client = make_client(access_token)
    bundle = await client.search(
        "DocumentReference",
        params={"patient": patient_reference(patient_id), "_sort": "-date", "_count": 20},
    )

    documents = []
    for resource in bundle_resources(bundle):
        documents.append({
            "title": resource.get("description") or (resource.get("type") or {}).get("text"),
            "status": resource.get("status"),
            "date": resource.get("date"),
        })
    return documents
