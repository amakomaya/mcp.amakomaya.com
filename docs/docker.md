# Docker Guide

The project ships as a **single application container** - there is no
database container, because the server holds no persistent state of its
own (all data lives in Keycloak and the FHIR server).

## Build and run

```bash
cp .env.example .env
# edit .env
docker compose up -d
```

This builds the image from the provided `Dockerfile` and starts one
container, `amakomaya-mcp`, listening on port `8000`.

## Useful commands

```bash
# View logs
docker compose logs -f amakomaya-mcp

# Rebuild after code changes
docker compose up -d --build

# Stop
docker compose down
```

## Health check

The container defines a `HEALTHCHECK` that polls `GET /health` every 30
seconds. Check container health with:

```bash
docker inspect --format='{{json .State.Health}}' amakomaya-mcp
```

## Image details

- Base image: `python:3.13-slim`
- Runs as a **non-root** user (`appuser`)
- Only `curl` is installed as an extra system package (used by the
  healthcheck)
