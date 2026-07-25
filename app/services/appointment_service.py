"""Appointment data, scoped to the authenticated patient."""
from __future__ import annotations

from app.services.base import bundle_resources, make_client, patient_reference


async def list_appointments(access_token: str, patient_id: str) -> list[dict]:
    client = make_client(access_token)
    bundle = await client.search(
        "Appointment",
        params={"patient": patient_reference(patient_id), "_sort": "date", "_count": 20},
    )

    appointments = []
    for resource in bundle_resources(bundle):
        appointments.append({
            "status": resource.get("status"),
            "start": resource.get("start"),
            "end": resource.get("end"),
            "type": (resource.get("appointmentType") or {}).get("text"),
            "description": resource.get("description"),
        })
    return appointments
