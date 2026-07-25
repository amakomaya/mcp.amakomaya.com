# Amakomaya MCP Server

An MCP (Model Context Protocol) server that lets Claude Desktop, Claude
Code, ChatGPT, Cursor, and other MCP clients securely access a patient's
**own** clinical information from the Amakomaya FHIR server.

## What this server does

- Authenticates users via **Keycloak** (OAuth2 Authorization Code + PKCE).
  No password ever touches this server.
- Resolves the signed-in user to exactly one FHIR **Patient** record.
- Exposes 9 simple MCP tools that always return **only that patient's own
  data** - there is no parameter for requesting anyone else's records.
- Talks to clinical data **only** through the FHIR REST API. No SQL, no
  ORM, no direct database access, no database container.

## What this server does NOT do

- It does not store any patient data itself.
- It does not connect directly to any database.
- It never exposes a raw FHIR Patient ID to the end user or MCP client.
- It never logs access tokens, refresh tokens, or clinical content.

## Architecture

```
Claude Desktop / Claude Code / ChatGPT / Cursor
        │  MCP over Streamable HTTP (Bearer <session token>)
        ▼
Amakomaya MCP Server  (this repo)
        │  OAuth2 Authorization Code + PKCE
        ▼
Keycloak  ──── issues signed JWT ────►  MCP Server validates
                                          (issuer, audience, expiry, signature)
        │  verified username/email
        ▼
FHIR REST API  ── Patient?identifier=<username> ──►  exactly one Patient
        │
        ▼
All further reads automatically scoped to that Patient
```

## Project structure

```
amakomaya-mcp/
├── app/
│   ├── auth/          Keycloak OAuth2/OIDC + JWT validation + sessions
│   ├── fhir/           FHIR REST client + patient identity resolution
│   ├── services/       One module per clinical domain (appointments, meds, ...)
│   ├── tools/          MCP tool definitions (the 9 tools Claude calls)
│   ├── middleware/      Auth + logging ASGI middleware
│   ├── config/         Settings (env-driven)
│   └── utils/           Errors + structured logging
├── tests/
├── docs/
├── main.py             FastAPI app: mounts MCP + OAuth endpoints
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Quick start

```bash
cp .env.example .env
# edit .env with your Keycloak + FHIR details
docker compose up -d
```

Then point an MCP client at `http://localhost:8000/mcp`, sign in via
`http://localhost:8000/auth/login`, and use the returned `session_token`
as the client's Bearer token.

See `docs/` for detailed guides:

- [Installation](docs/installation.md)
- [Docker](docs/docker.md)
- [Configuration](docs/configuration.md)
- [Developer Guide](docs/developer_guide.md)
- [Deployment](docs/deployment.md)

## MCP tools

| Tool | Description |
|---|---|
| `get_my_profile` | Your own name, gender, birth date, phone |
| `my_appointments` | Your own appointments |
| `my_medications` | Your own medications |
| `my_conditions` | Your own documented conditions |
| `my_observations` | Your own recorded vitals/labs (as documented, not interpreted) |
| `my_immunizations` | Your own immunization history |
| `my_documents` | Your own clinical documents |
| `my_clinical_summary` | A combined snapshot across the above |
| `server_status` | Health check |

## Security notes

- JWTs are validated for **signature** (against Keycloak's JWKS),
  **issuer**, **audience**, and **expiration** on every request.
- Only a service-account token is ever used for the one-time patient
  lookup step; all clinical reads use the signed-in user's own token.
- The FHIR Patient ID is stored **server-side only**, in an in-memory
  session keyed by an opaque session token - it is never returned to the
  client or accepted as an input parameter.
- Run `pytest` before every deploy: `pytest -q`.
