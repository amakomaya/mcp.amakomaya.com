"""
Amakomaya MCP Server - application entrypoint.

Wires together:
  - FastAPI app (health check only)
  - The MCP server (streamable HTTP transport), mounted at /mcp
  - Logging middleware

This build has no authentication or identity management - it is a
temporary development milestone focused purely on FHIR connectivity.
See README.md for what is intentionally not implemented yet.

Run locally:
    uvicorn main:app --host 0.0.0.0 --port 8000

Run with Docker:
    docker compose up -d
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import get_settings
from app.middleware.logging_middleware import LoggingMiddleware
from app.tools.register import mcp
from app.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("amakomaya.main")

_settings = get_settings()
logger.info("starting amakomaya-mcp fhir_base_url=%s", _settings.fhir_base_url)

mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_app.router.lifespan_context(mcp_app):
        yield


app = FastAPI(title="Amakomaya MCP Server", lifespan=lifespan)
app.add_middleware(LoggingMiddleware)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# mcp_app already serves the streamable HTTP transport at /mcp internally
# (FastMCP's default streamable_http_path), so it is mounted at "/" here -
# mounting it again at "/mcp" would require clients to hit /mcp/mcp, and
# hitting exactly "/mcp" would trigger a trailing-slash redirect that
# breaks behind reverse proxies that don't forward X-Forwarded-Proto.
# The /health route above is registered first so it takes priority over
# this catch-all mount.
app.mount("/", mcp_app)
