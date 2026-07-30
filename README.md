# Amakomaya Pregnancy Care MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/protocol-MCP-8A2BE2.svg)](https://modelcontextprotocol.io)

A single-purpose [Model Context Protocol](https://modelcontextprotocol.io)
server: a pregnant woman logs in with her phone number and Keycloak
password, and gets back a plain-language summary of her own pregnancy care
record -- pulled live from a FHIR R5 server -- through Claude or any other
MCP-compatible assistant. No app, no portal, no clinical jargon; just her
phone number and password.

---

## What it does

> *"Log me in with 9841234567 and my password."*

The assistant calls the one tool this server exposes. Behind that single
call:

1. Logs in to Keycloak with her phone number and password (OAuth2/OIDC).
2. Verifies the resulting access token's signature, expiry, and issuer
   against the realm's JWKS -- never trusts an unverified token.
3. Uses her verified phone number to find her FHIR `Patient` record
   (`Patient?identifier=<system>|<phone>`), saving its id.
4. Pulls her complete record with `Patient/{id}/$everything`.
5. Distills that into what actually matters to her: estimated due date and
   gestational age (if recorded), her ANC visit history, her next upcoming
   appointment, recent vitals/labs, anything flagged abnormal, her
   immunizations, and her current medications -- not a raw FHIR dump.

The assistant then explains that in plain language.

## The one tool

| Tool | What it does |
|---|---|
| `my_pregnancy_summary(username, password)` | Log in with phone number + password, return her pregnancy care summary |

That's the whole surface area, deliberately. This is a patient-facing
product, not a general FHIR toolkit -- no generic search, no create/update/
delete, nothing that isn't this one flow.

## Quick start

### 1. Install

```bash
git clone https://github.com/ahasan722/dhis2-mcp-server.git
cd dhis2-mcp-server

# with uv (recommended)
uv venv && source .venv/bin/activate
uv pip install -e .

# or with pip
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
# edit .env with your FHIR server, service-account credentials, and Keycloak realm
```

You need:
- A FHIR R5 server (`FHIR_BASE_URL`) with a service account it can use for
  every request (`FHIR_USERNAME`/`FHIR_PASSWORD` or `FHIR_TOKEN`)
- A Keycloak realm (`KEYCLOAK_ISSUER`) with a client
  (`KEYCLOAK_CLIENT_ID`) that has **Direct Access Grants** enabled -- that's
  what allows a username+password login instead of a browser redirect

### 3. Test with MCP Inspector

```bash
mcp dev src/digital_health_mcp/server.py
```

Open the Inspector, run `my_pregnancy_summary` with a real phone number and
password, and confirm the summary comes back.

### 4. Connect to Claude Desktop

Add to your `claude_desktop_config.json`
(`%APPDATA%\Claude\` on Windows,
`~/Library/Application Support/Claude/` on macOS):

```json
{
  "mcpServers": {
    "amakomaya-pregnancy": {
      "command": "digital-health-mcp",
      "env": {
        "FHIR_BASE_URL": "https://api.amakomaya.com",
        "FHIR_USERNAME": "fhir_admin",
        "FHIR_PASSWORD": "change-me",
        "KEYCLOAK_ISSUER": "https://keycloak.amakomaya.com/realms/amakomaya",
        "KEYCLOAK_CLIENT_ID": "amakomaya-mcp"
      }
    }
  }
}
```

Restart Claude Desktop. `my_pregnancy_summary` appears in the tools menu.

## Configuration reference

### FHIR R5

| Variable | Required | Description |
|---|---|---|
| `FHIR_BASE_URL` | yes | FHIR endpoint root, e.g. `https://api.amakomaya.com` |
| `FHIR_USERNAME` / `FHIR_PASSWORD` | one of | Service-account basic-auth credentials, used for every FHIR call |
| `FHIR_TOKEN` | one of | Service-account bearer token, preferred over username/password |
| `FHIR_PATIENT_IDENTIFIER_SYSTEM` | no | Identifier system used to match her phone number to her Patient resource (defaults to `https://api.amakomaya.com/nepal-telecome-system`) |
| `FHIR_VERIFY_SSL` | no | `false` for self-signed certs |
| `FHIR_TIMEOUT` | no | Request timeout in seconds (default 60) |

These service-account credentials authenticate every FHIR call this server
makes. They are read from the environment, never hardcoded in source, so
they never end up committed to git.

### Keycloak

| Variable | Required | Description |
|---|---|---|
| `KEYCLOAK_ISSUER` | yes | Realm URL, e.g. `https://keycloak.amakomaya.com/realms/amakomaya` |
| `KEYCLOAK_CLIENT_ID` | yes | Client with **Direct Access Grants** enabled |
| `KEYCLOAK_CLIENT_SECRET` | no | Only if the client is confidential |
| `KEYCLOAK_AUDIENCE` | no | If set, tokens must have this `aud` claim |
| `KEYCLOAK_JWKS_URL` / `KEYCLOAK_TOKEN_URL` | no | Overrides; default to `<issuer>/protocol/openid-connect/{certs,token}` |
| `KEYCLOAK_VERIFY_SSL` | no | `false` for self-signed certs |

## How identity works

The pregnant woman's Keycloak username **is her phone number**. Her
credentials are used only to prove who she is -- once
`my_pregnancy_summary` verifies her login, it looks up her FHIR record by
that same phone number and never touches her Keycloak credentials again.

Two deliberate security choices:

- **Her Keycloak token is never forwarded to the FHIR server.** FHIR calls
  always authenticate as the service account (`FHIR_TOKEN` or
  `FHIR_USERNAME`/`FHIR_PASSWORD`), not as her. This keeps the FHIR
  server's access model simple (one trusted service account) while still
  requiring her to prove her own identity before any of her data is
  fetched.
- **Every credential is read from the environment**, never hardcoded as a
  string literal in source, so nothing ends up committed to git or exposed
  if this repository is shared.

Login failures return a generic "incorrect phone number or password"
message -- Keycloak's internal error detail is never echoed back.

## Example session

```
You:  Log me in with 9841234567 and my password.
AI:   [my_pregnancy_summary] verified login, found her record
      You're about 28 weeks along, estimated due date March 14. Your last
      ANC visit was on January 5th, and your next appointment is scheduled
      for February 2nd. Your recent blood pressure and weight checks look
      normal. You're up to date on your TT vaccinations, and you're
      currently on iron and folic acid supplements.
```

## Architecture

```
src/digital_health_mcp/
├── server.py            # FastMCP instance; registers the one tool
└── fhir/
    ├── config.py        # FHIR service-account settings (env-driven)
    ├── client.py         # httpx wrapper -- auth, Bundle pagination,
    │                       OperationOutcome-aware error handling
    ├── auth.py            # Keycloak login (username+password) and
    │                        JWKS-verified access-token validation
    └── tools/
        └── pregnancy.py  # the one tool: login -> find Patient ->
                             $everything -> pregnancy-focused summary
```

## Security notes

- All credentials (FHIR service account, Keycloak client secret) are read
  from the environment, never hardcoded or sent to the model.
- `.env` is git-ignored. Do not commit credentials.
- `my_pregnancy_summary` verifies Keycloak tokens against the realm's JWKS
  (signature, expiry, issuer) before trusting any claim in them -- never
  decode a token without verification when using it for an authorization
  decision.
- This server defines no write/delete tools. It only reads.

## Development

```bash
pip install -e ".[dev]"
pytest          # config + auth tests, no live FHIR/Keycloak needed
ruff check .
```

## Roadmap

- [ ] Streamable HTTP transport for shared hosting
- [ ] Localized (Nepali) summary output

## License

MIT. See [LICENSE](LICENSE).
