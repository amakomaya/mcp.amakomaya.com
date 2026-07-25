"""Shared helpers for FHIR-backed services."""
from __future__ import annotations

from app.fhir.client import FHIRClient


def patient_reference(patient_id: str) -> str:
    return f"Patient/{patient_id}"


def bundle_resources(bundle: dict) -> list[dict]:
    """Extract the list of resources from a FHIR Bundle."""
    return [entry["resource"] for entry in bundle.get("entry", [])]


def make_client(access_token: str) -> FHIRClient:
    return FHIRClient(access_token=access_token)
