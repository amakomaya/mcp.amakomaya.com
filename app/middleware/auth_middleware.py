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
"""
from __future__ import annotations

from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth.models import AuthSession
from app.auth.session import session_store
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


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        new_request_id()

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
