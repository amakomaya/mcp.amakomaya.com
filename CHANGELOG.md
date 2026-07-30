# Changelog

All notable changes to this project are documented here.

## [Unreleased]

Pivoted from a general DHIS2+FHIR toolkit to a single-purpose product: a
pregnant woman logs in with her phone number and Keycloak password and gets
a plain-language summary of her own FHIR pregnancy record.

### Added
- `my_pregnancy_summary(username, password)` -- the server's one tool.
  Logs in to Keycloak with a phone-number username and password (OAuth2
  Resource Owner Password Credentials / "Direct Access Grants"), verifies
  the resulting token against the realm's JWKS, finds the matching FHIR
  `Patient` by that phone number, pulls the full record
  (`Patient/{id}/$everything`), and distills it into pregnancy-relevant
  highlights (estimated due date, gestational age, ANC visit history, next
  appointment, recent vitals/labs, anything flagged abnormal,
  immunizations, current medications) instead of a raw FHIR dump
  (`src/digital_health_mcp/fhir/auth.py`, `fhir/tools/pregnancy.py`)
- `KEYCLOAK_CLIENT_ID` (required) and `KEYCLOAK_CLIENT_SECRET`/
  `KEYCLOAK_TOKEN_URL` (optional) configuration for the Keycloak login
- `.gitignore` and `.env.example` for the new single-purpose config surface
- Keycloak auth test suite covering login and token verification with a
  mocked JWKS/token endpoint (`tests/test_keycloak_auth.py`)

### Removed
- The DHIS2 connector entirely (config, client, tools, tests) -- this
  server is FHIR-only now
- The generic FHIR toolkit (`fhir_search`, `fhir_read`, `fhir_create`,
  `fhir_update`, `fhir_patch`, `fhir_delete`, `fhir_validate`,
  `export_bundle`, `fhir_ping`, `fhir_capability_statement`) and the
  token-passed-in `my_patient_everything` tool it briefly replaced --
  narrower surface area and less risk for a patient-facing product

### Changed
- Package renamed from `dhis2_mcp` to `digital_health_mcp`; FHIR code lives
  in `src/digital_health_mcp/fhir/`. Console script is
  `digital-health-mcp`; distribution name is `digital-health-mcp-server`.
- Server identity renamed to `amakomaya-pregnancy`
- Transport env var renamed from `DHIS2_MCP_TRANSPORT` to `MCP_TRANSPORT`
  now that DHIS2 no longer exists in this codebase
- Pinned `mcp` to `>=1.2.0,<2.0` -- `mcp` 2.0.0 renamed
  `mcp.server.fastmcp.FastMCP`, which broke imports on a fresh install

## [0.1.0] - Initial release

### Added
- Environment-driven configuration that works with any DHIS2 instance
- Authentication via personal access token or basic auth
- HTTP client with transparent paging and friendly error messages
- Connection tools: `dhis2_ping`, `dhis2_whoami`, `dhis2_api_overview`
- Metadata discovery: `search_metadata`, `list_org_units`,
  `org_unit_children`, `list_data_sets`, `list_programs`
- Analytics: `get_analytics`, `get_analytics_raw`, `get_data_value_set`
- Tracker: `get_events`, `get_enrollments`
- Live `system/info` and relative-period resources
- `explore_instance` and `indicator_trend` prompts
- Config and import test suite
