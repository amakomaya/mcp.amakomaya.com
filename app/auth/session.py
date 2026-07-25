"""
Server-side session store.

Maps an opaque session id -> AuthSession (which holds the resolved FHIR
Patient ID and tokens). The Patient ID is NEVER sent to the client / user;
tools look it up internally via the current request's session id.

This in-memory implementation is fine for a single-instance deployment.
For multi-instance deployments, swap this for Redis (interface stays the
same - only the storage backend changes).
"""
from __future__ import annotations

import secrets
import time

from app.auth.models import AuthSession
from app.config.settings import get_settings
from app.utils.errors import UnauthorizedError


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, AuthSession] = {}

    def create(self, patient_id: str, access_token: str, refresh_token: str | None) -> str:
        settings = get_settings()
        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = AuthSession(
            session_id=session_id,
            patient_id=patient_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=time.time() + settings.session_ttl_seconds,
        )
        return session_id

    def get(self, session_id: str) -> AuthSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise UnauthorizedError("You need to sign in again to continue.")
        if session.expires_at < time.time():
            del self._sessions[session_id]
            raise UnauthorizedError("Your session has expired. Please sign in again.")
        return session

    def update_tokens(self, session_id: str, access_token: str, refresh_token: str | None) -> None:
        session = self.get(session_id)
        session.access_token = access_token
        if refresh_token:
            session.refresh_token = refresh_token
        settings = get_settings()
        session.expires_at = time.time() + settings.session_ttl_seconds

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


# Single shared instance for the process.
session_store = SessionStore()
