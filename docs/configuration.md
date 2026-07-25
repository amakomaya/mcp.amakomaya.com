# Configuration Guide

All configuration is via environment variables, loaded from `.env`
(see `.env.example`). Settings are validated at startup by
`app/config/settings.py` (a Pydantic `BaseSettings` model) - the process
will fail fast with a clear error if a required variable is missing.

## Keycloak

| Variable | Required | Description |
|---|---|---|
| `KEYCLOAK_URL` | yes | Base URL of your Keycloak instance |
| `KEYCLOAK_REALM` | yes | Realm name |
| `KEYCLOAK_CLIENT_ID` | yes | Client id registered for this MCP server |
| `KEYCLOAK_CLIENT_SECRET` | no | Only needed for confidential clients |
| `KEYCLOAK_REDIRECT_URI` | no | Must match a "Valid redirect URI" in Keycloak (default: `http://localhost:8000/auth/callback`) |

## FHIR

| Variable | Required | Description |
|---|---|---|
| `FHIR_BASE_URL` | yes | Base URL of the FHIR REST API, e.g. `https://fhir.amakomaya.com/fhir` |
| `FHIR_TIMEOUT` | no | Request timeout in seconds (default: `30`) |
| `FHIR_SERVICE_TOKEN` | yes | Bearer token used only for the one-time `Patient?identifier=` lookup |

## Server

| Variable | Required | Description |
|---|---|---|
| `HOST` | no | Bind address (default: `0.0.0.0`) |
| `PORT` | no | Bind port (default: `8000`) |
| `LOG_LEVEL` | no | `DEBUG` / `INFO` / `WARNING` / `ERROR` (default: `INFO`) |

## Session

| Variable | Required | Description |
|---|---|---|
| `SESSION_SECRET_KEY` | yes (production) | Used if/when the session store is swapped for a signed-cookie or Redis-backed implementation |
| `SESSION_TTL_SECONDS` | no | How long an MCP session stays valid before requiring re-login (default: `3600`) |

## Never commit `.env`

`.env.example` is the template. The real `.env` should never be committed
- it is already excluded from version control.
