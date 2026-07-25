"""
Aggregates a lightweight clinical summary from several resource types.

This is a convenience composition over the other services - it does not
call the FHIR server directly itself.
"""
from __future__ import annotations

import asyncio

from app.services import (
    appointment_service,
    condition_service,
    immunization_service,
    medication_service,
    observation_service,
    patient_service,
)


async def get_clinical_summary(access_token: str, patient_id: str) -> dict:
    (
        profile,
        appointments,
        medications,
        conditions,
        observations,
        immunizations,
    ) = await asyncio.gather(
        patient_service.get_profile(access_token, patient_id),
        appointment_service.list_appointments(access_token, patient_id),
        medication_service.list_medications(access_token, patient_id),
        condition_service.list_conditions(access_token, patient_id),
        observation_service.list_observations(access_token, patient_id),
        immunization_service.list_immunizations(access_token, patient_id),
    )

    return {
        "profile": profile,
        "upcoming_appointments": [a for a in appointments if a.get("status") == "booked"][:5],
        "active_medications": [m for m in medications if m.get("status") == "active"],
        "active_conditions": [c for c in conditions if c.get("clinical_status") == "active"],
        "recent_observations": observations[:10],
        "immunizations": immunizations,
    }
