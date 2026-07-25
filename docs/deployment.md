# Deployment Guide

## Recommended deployment shape

```
Internet
   │  HTTPS (terminate TLS here - e.g. at a reverse proxy / load balancer)
   ▼
Reverse proxy (nginx / Caddy / cloud LB)
   │  HTTP, internal network only
   ▼
amakomaya-mcp container (this repo)
   │                       │
   ▼                       ▼
Keycloak                FHIR server
```

This server should **never** be exposed directly to the internet without
TLS termination in front of it - Authorization headers and OAuth
redirects must travel over HTTPS end-to-end.

## Steps

1. Provision Keycloak and the FHIR server (or point at existing ones).
2. Set `KEYCLOAK_REDIRECT_URI` to the **public HTTPS** callback URL.
3. Build and push the image:
   ```bash
   docker build -t your-registry/amakomaya-mcp:latest .
   docker push your-registry/amakomaya-mcp:latest
   ```
4. Deploy the single container behind your reverse proxy / ingress,
   injecting `.env` values as real secrets (e.g. via your platform's
   secret manager) rather than a plain file.
5. Point your reverse proxy's health check at `GET /health`.
6. Verify `docs/installation.md`'s Keycloak checklist has been completed
   on the target realm.

## Scaling

The current session store is in-memory and per-process, so:

- A **single replica** is the simplest correct deployment.
- To run multiple replicas, swap `app/auth/session.py`'s in-memory dict
  for Redis (the `SessionStore` interface is designed so only the storage
  backend needs to change - `get`, `create`, `update_tokens`, `delete`).

## Rollback

Because the server is stateless (no database), rollback is simply
redeploying the previous image tag - there is no data migration to worry
about.

## Security testing

Any security/penetration testing must run against a **staging**
environment with its own Keycloak realm and FHIR test data - never
against production patient data, and only with documented authorization.
