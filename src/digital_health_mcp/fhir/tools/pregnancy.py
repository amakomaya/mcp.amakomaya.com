"""Self-service pregnancy record lookup for a Keycloak-authenticated user.

The whole flow behind one tool call: log in to Keycloak with a phone
number and password, verify the resulting token, find the matching FHIR
Patient by that phone number, pull her complete record ($everything), and
distill it into the handful of things that actually matter to a pregnant
woman -- due date, ANC visit history, next appointment, recent vitals,
anything flagged abnormal, immunizations, and current medications --
rather than a raw FHIR dump.

The Keycloak credentials are used only to establish identity. They are
never forwarded to the FHIR server -- those calls authenticate as the
service account configured via FHIR_TOKEN or FHIR_USERNAME/FHIR_PASSWORD
(see ../config.py), read from the environment rather than hardcoded.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from ..auth import KeycloakError, login_with_password
from ..client import get_client

DEFAULT_IDENTIFIER_SYSTEM = "https://api.amakomaya.com/nepal-telecome-system"

# LOINC codes commonly used to record these facts. Best-effort: if a site's
# FHIR data uses different codes, these highlights simply won't populate --
# the rest of the summary (encounters, observations, etc.) still will.
_EDD_CODES = {"11778-8", "11779-6", "11780-4"}
_GESTATIONAL_AGE_CODES = {"49051-6", "18185-9"}
_ABNORMAL_INTERPRETATION_CODES = {"A", "AA", "H", "HH", "L", "LL", "AB"}


def _human_name(patient: dict) -> str:
    names = patient.get("name", [])
    if not names:
        return "Unknown"
    n = names[0]
    full = f"{' '.join(n.get('given', []))} {n.get('family', '')}".strip()
    return full or n.get("text") or "Unknown"


def _phone(patient: dict) -> str:
    for t in patient.get("telecom", []):
        if t.get("system") == "phone":
            return t.get("value", "")
    return ""


def _code_text(concept: dict | None) -> str:
    if not concept:
        return ""
    if concept.get("text"):
        return concept["text"]
    codings = concept.get("coding", [])
    if codings:
        return codings[0].get("display") or codings[0].get("code", "")
    return ""


def _coding_codes(concept: dict | None) -> set:
    if not concept:
        return set()
    return {c.get("code") for c in concept.get("coding", []) if c.get("code")}


def _obs_value(obs: dict) -> str:
    if "valueQuantity" in obs:
        vq = obs["valueQuantity"]
        return f"{vq.get('value')} {vq.get('unit', '')}".strip()
    if "valueString" in obs:
        return obs["valueString"]
    if "valueCodeableConcept" in obs:
        return _code_text(obs["valueCodeableConcept"])
    if "valueBoolean" in obs:
        return str(obs["valueBoolean"])
    if "valueInteger" in obs:
        return str(obs["valueInteger"])
    if "valueDateTime" in obs:
        return obs["valueDateTime"]
    return ""


def _obs_date(obs: dict) -> str:
    return (
        obs.get("effectiveDateTime")
        or obs.get("issued")
        or (obs.get("effectivePeriod") or {}).get("start", "")
        or ""
    )


def _is_abnormal(obs: dict) -> bool:
    return any(
        _coding_codes(interp) & _ABNORMAL_INTERPRETATION_CODES
        for interp in obs.get("interpretation", [])
    )


def _medication_text(medication_request: dict) -> str:
    # FHIR R5 replaced the R4 medicationCodeableConcept/medicationReference
    # choice fields with a single medication CodeableReference.
    med = medication_request.get("medication") or {}
    if med.get("concept"):
        return _code_text(med["concept"])
    return (med.get("reference") or {}).get("display", "")


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _summarize_for_pregnancy(resources: list[dict]) -> dict:
    by_type: dict[str, list[dict]] = {}
    for r in resources:
        by_type.setdefault(r.get("resourceType", "Unknown"), []).append(r)

    patient = (by_type.get("Patient") or [{}])[0]

    pregnancy_conditions = [
        c
        for c in by_type.get("Condition", [])
        if "pregnan" in _code_text(c.get("code")).lower()
    ]

    observations = sorted(
        by_type.get("Observation", []), key=_obs_date, reverse=True
    )
    edd = next(
        (o for o in observations if _coding_codes(o.get("code")) & _EDD_CODES), None
    )
    gestational_age = next(
        (
            o
            for o in observations
            if _coding_codes(o.get("code")) & _GESTATIONAL_AGE_CODES
        ),
        None,
    )
    danger_signs = [
        {"finding": _code_text(o.get("code")), "value": _obs_value(o), "date": _obs_date(o)}
        for o in observations
        if _is_abnormal(o)
    ]

    # FHIR R5 renamed Encounter.period to Encounter.actualPeriod.
    encounters = sorted(
        by_type.get("Encounter", []),
        key=lambda e: (e.get("actualPeriod") or {}).get("start", ""),
        reverse=True,
    )
    most_recent_encounter = None
    if encounters:
        types = encounters[0].get("type") or []
        most_recent_encounter = {
            "date": (encounters[0].get("actualPeriod") or {}).get("start", ""),
            "type": _code_text(types[0]) if types else "",
        }

    immunizations = sorted(
        by_type.get("Immunization", []),
        key=lambda i: i.get("occurrenceDateTime", ""),
        reverse=True,
    )

    medications = [
        m
        for m in by_type.get("MedicationRequest", [])
        if m.get("status") in ("active", "on-hold")
    ]

    now = datetime.now(timezone.utc)
    upcoming = sorted(
        (
            a
            for a in by_type.get("Appointment", [])
            if (parsed := _parse_datetime(a.get("start", ""))) and parsed > now
        ),
        key=lambda a: a["start"],
    )

    return {
        "patient": {
            "name": _human_name(patient),
            "phone": _phone(patient),
            "birthDate": patient.get("birthDate", ""),
        },
        "pregnancyHighlights": {
            "activePregnancyCondition": (
                _code_text(pregnancy_conditions[0].get("code"))
                if pregnancy_conditions
                else None
            ),
            "estimatedDueDate": _obs_value(edd) if edd else None,
            "gestationalAge": _obs_value(gestational_age) if gestational_age else None,
        },
        "ancVisits": {"count": len(encounters), "mostRecent": most_recent_encounter},
        "upcomingAppointment": (
            {"date": upcoming[0].get("start"), "description": upcoming[0].get("description", "")}
            if upcoming
            else None
        ),
        "recentVitalsAndLabs": [
            {"finding": _code_text(o.get("code")), "value": _obs_value(o), "date": _obs_date(o)}
            for o in observations[:10]
        ],
        "possibleDangerSigns": danger_signs,
        "immunizations": [
            {
                "vaccine": _code_text(i.get("vaccineCode")),
                "date": i.get("occurrenceDateTime", ""),
                "status": i.get("status"),
            }
            for i in immunizations
        ],
        "currentMedications": [
            {"medication": _medication_text(m), "status": m.get("status")}
            for m in medications
        ],
        "resourceCount": len(resources),
    }


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def my_pregnancy_summary(username: str, password: str) -> str:
        """Log a pregnant woman in with her phone number and password, then
        return a plain-language summary of her pregnancy care record.

        Logs in to Keycloak with the given credentials (username is her
        phone number), verifies the resulting token, finds her FHIR Patient
        record by that phone number, pulls her complete record
        ($everything), and distills it into what matters to her: estimated
        due date and gestational age (if recorded), ANC visit history, the
        next upcoming appointment, recent vitals/labs, any findings flagged
        abnormal, immunizations, and current medications.

        Args:
            username: her Keycloak login username -- her phone number.
            password: her Keycloak login password.
        """
        try:
            verified_username = login_with_password(username, password)
        except KeycloakError as exc:
            return f"Login failed: {exc}"

        identifier_system = os.environ.get(
            "FHIR_PATIENT_IDENTIFIER_SYSTEM", DEFAULT_IDENTIFIER_SYSTEM
        )
        matches = get_client().get_all_bundle_entries(
            "Patient",
            params={"identifier": f"{identifier_system}|{verified_username}"},
            max_records=1,
        )
        if not matches:
            return f"No patient record found for '{verified_username}'."
        patient_id = matches[0]["id"]

        resources = get_client().get_all_bundle_entries(
            f"Patient/{patient_id}/$everything", max_records=1000
        )
        summary = _summarize_for_pregnancy(resources)
        summary["savedPersonId"] = patient_id
        return json.dumps(summary, indent=2)
