"""Patient demographic / profile data."""
from __future__ import annotations

from app.services.base import make_client


async def get_profile(access_token: str, patient_id: str) -> dict:
    client = make_client(access_token)
    patient = await client.read("Patient", patient_id)

    name = patient.get("name", [{}])[0]
    full_name = " ".join(filter(None, [
        " ".join(name.get("given", [])),
        name.get("family", ""),
    ])).strip()

    return {
        "name": full_name or "Not on file",
        "gender": patient.get("gender"),
        "birth_date": patient.get("birthDate"),
        "phone": next(
            (t["value"] for t in patient.get("telecom", []) if t.get("system") == "phone"),
            None,
        ),
    }
