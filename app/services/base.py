"""Shared helpers for FHIR-backed services."""
from __future__ import annotations

from typing import Any


def bundle_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    """Flatten a FHIR Bundle into a total count plus the raw resources."""
    return {
        "total": bundle.get("total", len(bundle.get("entry", []))),
        "resources": [entry["resource"] for entry in bundle.get("entry", []) if "resource" in entry],
    }
