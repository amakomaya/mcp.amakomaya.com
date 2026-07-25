"""Data models for authentication."""
from __future__ import annotations

from pydantic import BaseModel


class TokenClaims(BaseModel):
    """The subset of JWT claims we actually need, after validation."""

    sub: str
    preferred_username: str | None = None
    email: str | None = None
    iss: str
    aud: str | list[str]
    exp: int

    @property
    def identifier(self) -> str:
        """The value used to look up the FHIR Patient record."""
        return self.preferred_username or self.email or self.sub


class AuthSession(BaseModel):
    """
    Server-side session created after a successful login.

    Only the FHIR Patient ID is stored here for use by tools - it is never
    sent back to the client / user.
    """

    session_id: str
    patient_id: str
    access_token: str
    refresh_token: str | None = None
    expires_at: float
