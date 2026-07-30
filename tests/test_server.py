"""Server-level smoke test. No live FHIR/Keycloak connection needed."""

import asyncio
import importlib


def test_server_imports_and_registers_tool():
    mod = importlib.import_module("digital_health_mcp.server")
    assert mod.mcp.name == "amakomaya-pregnancy"

    tools = asyncio.run(mod.mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {"my_pregnancy_summary"}
