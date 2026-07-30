"""Configuration loaded from environment variables.

Works with any FHIR R5 server (HAPI FHIR or otherwise). Set FHIR_BASE_URL
plus, if the server requires it, a bearer token (FHIR_TOKEN) or basic-auth
credentials (FHIR_USERNAME / FHIR_PASSWORD). Token is preferred when both are
present. Many public/test FHIR servers accept anonymous access, so unlike
DHIS2 credentials are optional here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or inconsistent."""


def _clean_base_url(raw: str) -> str:
    """Normalise the base URL so callers never end up with a trailing slash.

    Accepts forms like:
        https://hapi.fhir.org/baseR5
        https://hapi.fhir.org/baseR5/
    and returns the FHIR endpoint root without a trailing slash.
    """
    return raw.strip().rstrip("/")


@dataclass(frozen=True)
class Settings:
    base_url: str
    username: str | None
    password: str | None
    token: str | None
    verify_ssl: bool
    timeout: float

    @property
    def uses_token(self) -> bool:
        return bool(self.token)


def load_settings() -> Settings:
    base = os.environ.get("FHIR_BASE_URL", "").strip()
    if not base:
        raise ConfigError(
            "FHIR_BASE_URL is not set. Point it at any FHIR R5 endpoint, "
            "for example https://hapi.fhir.org/baseR5"
        )

    token = os.environ.get("FHIR_TOKEN", "").strip() or None
    user = os.environ.get("FHIR_USERNAME", "").strip() or None
    pwd = os.environ.get("FHIR_PASSWORD", "").strip() or None

    verify = os.environ.get("FHIR_VERIFY_SSL", "true").strip().lower() not in (
        "false",
        "0",
        "no",
    )
    timeout = float(os.environ.get("FHIR_TIMEOUT", "60"))

    return Settings(
        base_url=_clean_base_url(base),
        username=user,
        password=pwd,
        token=token,
        verify_ssl=verify,
        timeout=timeout,
    )
