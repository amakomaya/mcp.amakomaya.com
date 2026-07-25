# Installation Guide

## Prerequisites

- Python 3.13
- A running Keycloak realm with a confidential or public client configured
  for the Authorization Code + PKCE flow
- A FHIR R5-compatible server reachable over HTTPS
- (Optional) Docker + Docker Compose, for the containerized path

## Local (no Docker)

```bash
git clone <this-repo>
cd amakomaya-mcp

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# edit .env - see docs/configuration.md

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's up:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## Keycloak setup checklist

1. Create a client (e.g. `amakomaya-mcp`) with:
   - **Standard flow** (Authorization Code) enabled
   - **PKCE method**: S256
   - **Valid redirect URIs**: matches `KEYCLOAK_REDIRECT_URI` in `.env`
2. Add an **audience mapper** on the client so the access token's `aud`
   claim includes the client id (Keycloak's default `account` audience
   will not pass validation otherwise).
3. Confirm `preferred_username` (or `email`) is included in the access
   token - this is what the server uses to look up the FHIR Patient.
4. Create a separate **service account client** (client credentials
   grant) for the one-time Patient lookup step, and put its token in
   `FHIR_SERVICE_TOKEN` - or configure it to obtain a fresh token
   automatically if your FHIR server issues short-lived tokens
   (see `docs/developer_guide.md`).

## FHIR server checklist

- Patient resources must have an `identifier` matching the Keycloak
  `preferred_username`/`email` your users log in with.
- The service account used for `FHIR_SERVICE_TOKEN` needs **read** access
  to `Patient` (search only - it should not be able to read clinical
  resources for arbitrary patients).
