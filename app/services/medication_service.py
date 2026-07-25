"""Medication request data, scoped to the authenticated patient."""
from __future__ import annotations

from app.services.base import bundle_resources, make_client, patient_reference


async def list_medications(access_token: str, patient_id: str) -> list[dict]:
    client = make_client(access_token)
    bundle = await client.search(
        "MedicationRequest",
        params={"patient": patient_reference(patient_id), "_sort": "-authoredon", "_count": 20},
    )

    medications = []
    for resource in bundle_resources(bundle):
        med_text = (resource.get("medicationCodeableConcept") or {}).get("text")
        dosage_instructions = resource.get("dosageInstruction", [])
        dosage_text = dosage_instructions[0].get("text") if dosage_instructions else None

        medications.append({
            "medication": med_text,
            "status": resource.get("status"),
            "dosage": dosage_text,
            "authored_on": resource.get("authoredOn"),
        })
    return medications
