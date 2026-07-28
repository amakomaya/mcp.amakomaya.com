# Amakomaya MCP Server

An MCP (Model Context Protocol) server that connects Claude Desktop, Claude
Code, ChatGPT, Cursor, and other MCP clients to a FHIR server over the
FHIR REST API.

## Milestone: FHIR connectivity, no authentication

This build is a **temporary development milestone**. It intentionally has
**no authentication or identity management** - no OAuth2, no OpenID
Connect, no Keycloak, no PKCE, no JWT validation, no sessions, no login
endpoints, no user identity resolution, no authorization middleware, no
RBAC, no patient-ownership checks. Every tool takes an explicit FHIR
resource id or patient id from the caller.

The goal of this milestone is only to:

1. Start successfully.
2. Connect to the configured FHIR server.
3. Read resources using the FHIR REST API.
4. Return valid responses through MCP tools.
5. Be easy to extend with real authentication later.

**Do not deploy this build anywhere it would be reachable by untrusted
clients or expose real patient data** - it has no access control of any
kind.

## What this server does

- Talks to clinical data **only** through the FHIR REST API. No SQL, no
  ORM, no direct database access, no database container.
- Automatically authenticates to the *FHIR server itself* (not the end
  user) using whichever of Bearer token / Basic auth / no auth is
  configured via environment variables.
- Exposes 9 MCP tools for reading FHIR resources by id or search
  parameters.

## Architecture

```
Claude Desktop / Claude Code / ChatGPT / Cursor
        │  MCP over Streamable HTTP
        ▼
Amakomaya MCP Server  (this repo)
        │  HTTP(S), auto-selected auth: Bearer token > Basic auth > none
        ▼
FHIR REST API
```

## Project structure

```
amakomaya-mcp/
├── app/
│   ├── config/          Settings (env-driven)
│   ├── fhir/
│   │   └── client.py     Reusable async FHIR REST client
│   ├── services/         One module per FHIR resource type
│   ├── tools/             MCP tool definitions
│   ├── middleware/       Request logging ASGI middleware
│   └── utils/             Errors + structured logging
├── tests/
├── main.py               FastAPI app: mounts the MCP server + /health
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Configuration

All configuration is environment variables (see `.env.example`):

```
FHIR_BASE_URL=http://localhost:8080/fhir
FHIR_TIMEOUT=30
FHIR_MAX_RETRIES=3

FHIR_USERNAME=
FHIR_PASSWORD=
FHIR_TOKEN=
```

`FHIRClient` (`app/fhir/client.py`) picks the auth mode automatically:

1. `FHIR_TOKEN` set → Bearer token auth.
2. Otherwise, `FHIR_USERNAME` + `FHIR_PASSWORD` set → HTTP Basic auth.
3. Otherwise → no authentication.

## Quick start

```bash
cp .env.example .env
# edit .env with your FHIR server details
docker compose up -d
```

Or locally without Docker:

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then point an MCP client at `http://localhost:8000/mcp`. No sign-in step
is required in this build.

## MCP tools

| Tool | Description |
|---|---|
| `server_status` | MCP server health + FHIR server connectivity + FHIR version |
| `get_patient` | Retrieve a Patient resource by FHIR id |
| `search_patients` | Search patients by family name, given name, identifier, or birth date |
| `get_observation` | Retrieve an Observation by FHIR id |
| `search_observations` | Search Observations for a patient FHIR id |
| `get_encounter` | Retrieve an Encounter by FHIR id |
| `search_encounters` | Search Encounters for a patient FHIR id |
| `search_medications` | Search MedicationRequest resources for a patient FHIR id |
| `raw_fhir` | Execute a raw GET request against any FHIR endpoint, for debugging |

## Testing

```bash
pytest -q
```

## Roadmap

Authentication (Keycloak OAuth2/OIDC + PKCE, JWT validation, sessions,
patient-identity resolution, authorization middleware, RBAC) is planned
for a later milestone, once FHIR connectivity is verified end-to-end. It
is out of scope for this build by design.
