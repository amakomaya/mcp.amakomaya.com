"""Thin, well-behaved HTTP client for a FHIR R5 server.

Handles authentication (bearer token or basic auth), sensible defaults,
Bundle-link pagination for search results, and friendly error messages --
including surfacing FHIR OperationOutcome detail -- so the language model
gets something actionable when a call fails.
"""

from __future__ import annotations

from typing import Any

import httpx

from .config import Settings, load_settings

FHIR_JSON = "application/fhir+json"


class FHIRError(RuntimeError):
    """Raised when the FHIR server returns an error or is unreachable."""


def _operation_outcome_detail(r: httpx.Response) -> str:
    """Extract a readable message from a FHIR OperationOutcome, if present."""
    try:
        body = r.json()
    except ValueError:
        return r.text[:500]
    if isinstance(body, dict) and body.get("resourceType") == "OperationOutcome":
        parts = [
            issue.get("diagnostics")
            or issue.get("details", {}).get("text")
            or issue.get("code", "")
            for issue in body.get("issue", [])
        ]
        detail = "; ".join(p for p in parts if p)
        if detail:
            return detail
    return r.text[:500]


class FHIRClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self._client = self._build_client()

    def _build_client(self) -> httpx.Client:
        s = self.settings
        headers = {"Accept": FHIR_JSON}
        auth: httpx.Auth | None = None
        if s.uses_token:
            headers["Authorization"] = f"Bearer {s.token}"
        elif s.username and s.password:
            auth = httpx.BasicAuth(s.username, s.password)
        return httpx.Client(
            base_url=s.base_url,
            headers=headers,
            auth=auth,
            timeout=s.timeout,
            verify=s.verify_ssl,
            follow_redirects=True,
        )

    # ------------------------------------------------------------------ #
    # Core verbs
    # ------------------------------------------------------------------ #
    def get(self, path: str, params: Any = None) -> Any:
        """GET a resource. `path` is relative to the FHIR base, e.g.
        'Patient/123', or an absolute URL (used for pagination links)."""
        try:
            r = self._client.get(path.lstrip("/"), params=params)
        except httpx.RequestError as exc:
            raise FHIRError(
                f"Could not reach FHIR server at {self.settings.base_url}: {exc}"
            ) from exc
        return self._handle(r)

    def post(self, path: str, json: Any = None, params: Any = None) -> Any:
        try:
            r = self._client.post(
                path.lstrip("/"),
                json=json,
                params=params,
                headers={"Content-Type": FHIR_JSON} if json is not None else None,
            )
        except httpx.RequestError as exc:
            raise FHIRError(f"Request to FHIR server failed: {exc}") from exc
        return self._handle(r)

    def put(self, path: str, json: Any) -> Any:
        try:
            r = self._client.put(
                path.lstrip("/"), json=json, headers={"Content-Type": FHIR_JSON}
            )
        except httpx.RequestError as exc:
            raise FHIRError(f"Request to FHIR server failed: {exc}") from exc
        return self._handle(r)

    def patch(self, path: str, patch_document: Any) -> Any:
        """Apply a JSON Patch (RFC 6902) document to a resource."""
        try:
            r = self._client.patch(
                path.lstrip("/"),
                json=patch_document,
                headers={"Content-Type": "application/json-patch+json"},
            )
        except httpx.RequestError as exc:
            raise FHIRError(f"Request to FHIR server failed: {exc}") from exc
        return self._handle(r)

    def delete(self, path: str) -> Any:
        try:
            r = self._client.delete(path.lstrip("/"))
        except httpx.RequestError as exc:
            raise FHIRError(f"Request to FHIR server failed: {exc}") from exc
        return self._handle(r)

    def _handle(self, r: httpx.Response) -> Any:
        if r.status_code == 401:
            raise FHIRError(
                "Authentication failed (401). Check FHIR_TOKEN or "
                "FHIR_USERNAME / FHIR_PASSWORD."
            )
        if r.status_code == 403:
            raise FHIRError(
                "Access denied (403). The account lacks authority for this "
                "resource."
            )
        if r.status_code >= 400:
            raise FHIRError(
                f"FHIR server returned {r.status_code}: {_operation_outcome_detail(r)}"
            )
        if r.status_code == 204 or not r.content:
            return {"status": "ok", "httpStatus": r.status_code}
        ctype = r.headers.get("content-type", "")
        if "json" in ctype:
            return r.json()
        return r.text

    # ------------------------------------------------------------------ #
    # Bundle pagination helper
    # ------------------------------------------------------------------ #
    def get_all_bundle_entries(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        max_records: int = 200,
    ) -> list[dict[str, Any]]:
        """Follow Bundle.link[relation=next] and collect up to `max_records`
        resources from a search result."""
        query: dict[str, Any] | None = dict(params or {})
        query.setdefault("_count", min(max_records, 100))
        out: list[dict[str, Any]] = []
        next_url: str | None = path
        while next_url:
            data = self.get(next_url, params=query)
            query = None  # only needed on the first request; links are absolute
            entries = data.get("entry", []) if isinstance(data, dict) else []
            out.extend(e.get("resource", e) for e in entries)
            if len(out) >= max_records:
                return out[:max_records]
            links = {
                link.get("relation"): link.get("url")
                for link in (data.get("link", []) if isinstance(data, dict) else [])
            }
            next_url = links.get("next")
        return out

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------- #
# Lazy singleton so tools share one connection without reconnecting.
# ---------------------------------------------------------------------- #
_client: FHIRClient | None = None


def get_client() -> FHIRClient:
    global _client
    if _client is None:
        _client = FHIRClient()
    return _client
