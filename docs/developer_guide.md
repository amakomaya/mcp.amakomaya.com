# Developer Guide

Welcome! This project is intentionally small - you should be able to
understand the whole request path within an hour.

## Request path, end to end

1. **`main.py`** wires together the FastAPI app: the OAuth endpoints
   (`/auth/login`, `/auth/callback`) and the mounted MCP app (`/mcp`).
2. **`app/middleware/auth_middleware.py`** runs on every `/mcp` request.
   It reads the `Authorization: Bearer <session_id>` header, looks the
   session up in `app/auth/session.py`, and stashes it in a contextvar.
3. **`app/tools/register.py`** defines the 9 MCP tools. Each one calls
   `get_current_session()` to get the current patient's id + access
   token, then delegates to a function in `app/services/`.
4. **`app/services/*.py`** each call `app/fhir/client.py` to hit one FHIR
   resource type, and reshape the response into a simple dict - no FHIR
   jargon leaks past this layer.
5. **`app/fhir/client.py`** is the only module that makes HTTP calls to
   the FHIR server. It translates HTTP status codes into the friendly
   errors defined in `app/utils/errors.py`.

## Adding a new tool

1. Add a service function in `app/services/` that calls
   `app/fhir/client.py` and returns a plain dict/list.
2. Register a new `@mcp.tool()` function in `app/tools/register.py` that
   calls `get_current_session()` and your new service function, wrapped
   in `_run(...)`.
3. Add a test in `tests/`.

That's it - you do not need to touch auth, middleware, or the FHIR client
for a typical new read-only tool.

## Login flow, for local testing

1. `GET /auth/login` → redirects to Keycloak.
2. Log in on Keycloak's hosted page.
3. Keycloak redirects to `/auth/callback?code=...&state=...`.
4. The server exchanges the code for tokens, validates the JWT, resolves
   the Patient, and returns a `session_token`.
5. Use that `session_token` as the Bearer token for all `/mcp` requests.

## Testing

```bash
pip install -r requirements.txt
pytest -q
```

Tests use `respx` to mock the FHIR server - no real Keycloak or FHIR
instance is needed to run the test suite.

## Coding conventions

- Type hints everywhere.
- Functions stay under ~50 lines - if a service function grows past
  that, it's a sign it should be split.
- No abstraction layers beyond `services` → `fhir` client - resist the
  urge to add repositories, factories, or generic base classes that
  aren't already justified by real duplication.
- Every error the user can see must come from `app/utils/errors.py`
  (`AppError` subclasses) - never let a raw exception message reach a
  tool's return value.

## Things to verify against your exact dependency versions

- The `mcp` (Model Context Protocol Python SDK) API surface changes
  between releases. `app/tools/register.py` uses
  `mcp.server.fastmcp.FastMCP` and `mcp.streamable_http_app()` /
  `mcp.list_tools()`, which were verified against the SDK version pinned
  in `requirements.txt` - re-check these calls if you upgrade the `mcp`
  package.
- Keycloak's default access token audience is often `account`, not your
  client id - add an audience mapper (see `docs/installation.md`) or
  adjust `app/auth/jwt_validator.py`'s `audience` check accordingly.
