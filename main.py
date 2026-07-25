"""
Amakomaya MCP Server - application entrypoint.

Wires together:
  - FastAPI app (for the OAuth login/callback endpoints + health check)
  - The MCP server (streamable HTTP transport), mounted at /mcp
  - Auth + logging middleware

Run locally:
    uvicorn main:app --host 0.0.0.0 --port 8000

Run with Docker:
    docker compose up -d
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth.jwt_validator import validate_access_token
from app.auth.keycloak import (
    build_authorization_url,
    exchange_code_for_tokens,
    generate_pkce_challenge,
)
from app.auth.session import session_store
from app.fhir.patient_resolver import resolve_patient_id
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.tools.register import mcp
from app.utils.errors import AppError
from app.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("amakomaya.main")

# In-memory PKCE state store, keyed by the OAuth `state` parameter.
# Short-lived: entries are consumed at the /auth/callback step.
_pending_logins: dict[str, str] = {}

mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_app.router.lifespan_context(mcp_app):
        yield


app = FastAPI(title="Amakomaya MCP Server", lifespan=lifespan)
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)

app.mount("/mcp", mcp_app)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/auth/login")
async def login() -> RedirectResponse:
    """Redirect the user to Keycloak's hosted login page (PKCE flow)."""
    pkce = generate_pkce_challenge()
    _pending_logins[pkce.state] = pkce.verifier
    return RedirectResponse(url=build_authorization_url(pkce))


@app.get("/auth/callback")
async def callback(request: Request):
    """
    Handle the redirect back from Keycloak: exchange the code for tokens,
    resolve the patient's identity, and issue an opaque MCP session id.
    """
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code or not state or state not in _pending_logins:
        return JSONResponse(status_code=400, content={"error": "Invalid or expired login attempt."})

    verifier = _pending_logins.pop(state)

    try:
        tokens = await exchange_code_for_tokens(code, verifier)
        claims = await validate_access_token(tokens["access_token"])
        patient_id = await resolve_patient_id(claims.identifier)
    except AppError as exc:
        logger.info("login_failed status=%s", exc.status_code)
        return JSONResponse(status_code=exc.status_code, content={"error": exc.friendly_message})

    session_id = session_store.create(
        patient_id=patient_id,
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
    )

    # This session id is what the MCP client (Claude Desktop, etc.) should
    # send as its Bearer token on every subsequent MCP request.
    return {
        "message": "Login successful. You can now return to your MCP client.",
        "session_token": session_id,
    }
