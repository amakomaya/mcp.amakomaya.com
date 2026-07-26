"""
ASGI middleware that authenticates every MCP request.

Flow per request:
  1. Extract "Authorization: Bearer <session_id>" header.
     (The value handed to MCP clients is our own opaque session id,
     returned at the end of the OAuth callback - never the raw Keycloak
     access token and never the FHIR Patient ID.)
  2. Look up the session in the session store.
  3. Refresh the underlying Keycloak access token if it's close to expiry.
  4. Stash the session in a contextvar so tools can use it without any
     of this plumbing leaking into `app/tools`.

If authentication fails, the request is rejected before it reaches any
tool - tools can assume `get_current_session()` always succeeds.

TODO(auth): AUTH_ENABLED=false (see app/config/settings.py) temporarily
bypasses all of the above and serves every request as a fixed patient.
Remove this bypass once the MCP protocol wiring is verified.
"""
from __future__ import annotations

import time
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth.models import AuthSession
from app.auth.session import session_store
from app.config.settings import get_settings
from app.utils.errors import AppError, UnauthorizedError
from app.utils.logging import get_logger, new_request_id

logger = get_logger("amakomaya.middleware.auth")

_current_session: ContextVar[AuthSession | None] = ContextVar("current_session", default=None)

# Paths that do not require an authenticated MCP session.
_PUBLIC_PATHS = {"/auth/login", "/auth/callback", "/health"}


def get_current_session() -> AuthSession:
    session = _current_session.get()
    if session is None:
        raise UnauthorizedError("You need to sign in again to continue.")
    return session


def _auth_disabled_session() -> AuthSession:
    """
    TODO(auth): remove once AUTH_ENABLED is restored to always-True.

    Stands in for a real session while auth is switched off, so tools
    (which all call get_current_session()) keep working against a single
    fixed patient instead of raising UnauthorizedError on every call.
    """
    settings = get_settings()
    return AuthSession(
        session_id="auth-disabled",
        patient_id=settings.auth_disabled_patient_id,
        access_token=settings.fhir_service_token,
        refresh_token=None,
        expires_at=time.time() + settings.session_ttl_seconds,
    )


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        new_request_id()

        settings = get_settings()

        # TODO(auth): temporary bypass - see AUTH_ENABLED in
        # app/config/settings.py. Skips Keycloak/session auth entirely and
        # every request is served as settings.auth_disabled_patient_id.
        if not settings.auth_enabled:
            token = _current_session.set(_auth_disabled_session())
            try:
                return await call_next(request)
            finally:
                _current_session.reset(token)

        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return _error_response(UnauthorizedError())

        session_id = auth_header.split(" ", 1)[1].strip()

        try:
            session = session_store.get(session_id)
        except AppError as exc:
            return _error_response(exc)

        token = _current_session.set(session)
        try:
            return await call_next(request)
        finally:
            _current_session.reset(token)


def _error_response(exc: AppError) -> JSONResponse:
    logger.info("request_rejected status=%s", exc.status_code)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.friendly_message})
