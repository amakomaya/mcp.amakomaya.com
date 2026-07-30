"""Amakomaya Pregnancy Care MCP Server.

A single-purpose MCP server: a pregnant woman logs in with her phone number
and Keycloak password, and gets back a plain-language summary of her own
pregnancy care record pulled from a FHIR R5 server. Configure with
environment variables (see .env.example) and the server connects to
whatever FHIR server and Keycloak realm you point it at.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from .fhir.tools import pregnancy

# Host/port matter only for the HTTP transport (remote / browser connector).
# Hosting platforms inject a PORT env var; bind 0.0.0.0 so it is reachable.
mcp = FastMCP(
    "amakomaya-pregnancy",
    host=os.environ.get("HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", "8000")),
    instructions=(
        "You are helping a pregnant woman check on her own pregnancy care "
        "record. Ask for her phone number (her Keycloak username) and her "
        "password, then call my_pregnancy_summary with those credentials. "
        "Never ask her for a Patient id or any FHIR identifier -- the tool "
        "resolves that automatically from her phone number. Explain the "
        "result in warm, plain language, not clinical jargon. If "
        "possibleDangerSigns is non-empty, gently flag that she should "
        "contact her health worker, without causing alarm. If login fails, "
        "ask her to double check her phone number and password rather than "
        "repeating the raw error."
    ),
)

pregnancy.register(mcp)


def main() -> None:
    """Console entry point.

    Transport is chosen by the MCP_TRANSPORT env var:
      stdio (default) -> local use with Claude Desktop / Claude Code
      http            -> remote streamable-HTTP for browser custom connectors,
                         served at http://<host>:<port>/mcp
    """
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport in ("http", "streamable-http", "streamable_http"):
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
