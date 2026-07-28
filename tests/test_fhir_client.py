import httpx
import pytest
import respx
from httpx import Response

from app.config.settings import Settings
from app.fhir.client import FHIRClient
from app.utils.errors import ForbiddenError, InternalError, NotFoundError, TimeoutErrorApp, UnauthorizedError

BASE_URL = "https://fhir.test/fhir"


def _settings(**overrides) -> Settings:
    return Settings(fhir_base_url=BASE_URL, fhir_max_retries=2, **overrides)


@pytest.mark.asyncio
@respx.mock
async def test_read_success():
    respx.get(f"{BASE_URL}/Patient/1").mock(return_value=Response(200, json={"resourceType": "Patient", "id": "1"}))
    client = FHIRClient(_settings())
    result = await client.read("Patient", "1")
    assert result == {"resourceType": "Patient", "id": "1"}


@pytest.mark.asyncio
@respx.mock
async def test_search_success():
    respx.get(f"{BASE_URL}/Observation").mock(return_value=Response(200, json={"entry": []}))
    client = FHIRClient(_settings())
    result = await client.search("Observation", params={"patient": "1"})
    assert result == {"entry": []}


@pytest.mark.asyncio
@respx.mock
async def test_no_auth_sends_no_authorization_header():
    route = respx.get(f"{BASE_URL}/Patient").mock(return_value=Response(200, json={}))
    client = FHIRClient(_settings())
    await client.search("Patient")
    assert "authorization" not in route.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
async def test_bearer_token_sets_authorization_header():
    route = respx.get(f"{BASE_URL}/Patient").mock(return_value=Response(200, json={}))
    client = FHIRClient(_settings(fhir_token="secret-token"))
    await client.search("Patient")
    assert route.calls.last.request.headers["authorization"] == "Bearer secret-token"


@pytest.mark.asyncio
@respx.mock
async def test_basic_auth_used_when_no_token():
    route = respx.get(f"{BASE_URL}/Patient").mock(return_value=Response(200, json={}))
    client = FHIRClient(_settings(fhir_username="alice", fhir_password="hunter2"))
    await client.search("Patient")
    assert route.calls.last.request.headers["authorization"].startswith("Basic ")


@pytest.mark.asyncio
@respx.mock
async def test_token_takes_priority_over_basic_auth():
    route = respx.get(f"{BASE_URL}/Patient").mock(return_value=Response(200, json={}))
    client = FHIRClient(_settings(fhir_token="secret-token", fhir_username="alice", fhir_password="hunter2"))
    await client.search("Patient")
    assert route.calls.last.request.headers["authorization"] == "Bearer secret-token"


@pytest.mark.asyncio
@respx.mock
async def test_search_unauthorized():
    respx.get(f"{BASE_URL}/Patient").mock(return_value=Response(401))
    client = FHIRClient(_settings())
    with pytest.raises(UnauthorizedError):
        await client.search("Patient")


@pytest.mark.asyncio
@respx.mock
async def test_search_forbidden():
    respx.get(f"{BASE_URL}/Patient").mock(return_value=Response(403))
    client = FHIRClient(_settings())
    with pytest.raises(ForbiddenError):
        await client.search("Patient")


@pytest.mark.asyncio
@respx.mock
async def test_search_not_found():
    respx.get(f"{BASE_URL}/Patient").mock(return_value=Response(404))
    client = FHIRClient(_settings())
    with pytest.raises(NotFoundError):
        await client.search("Patient")


@pytest.mark.asyncio
@respx.mock
async def test_search_timeout_after_retries():
    respx.get(f"{BASE_URL}/Patient").mock(side_effect=httpx.TimeoutException("timeout"))
    client = FHIRClient(_settings())
    with pytest.raises(TimeoutErrorApp):
        await client.search("Patient")


@pytest.mark.asyncio
@respx.mock
async def test_retryable_status_then_success():
    route = respx.get(f"{BASE_URL}/Patient")
    route.side_effect = [Response(503), Response(200, json={"ok": True})]
    client = FHIRClient(_settings())
    result = await client.search("Patient")
    assert result == {"ok": True}
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_retryable_status_exhausts_retries():
    respx.get(f"{BASE_URL}/Patient").mock(return_value=Response(503))
    client = FHIRClient(_settings())
    with pytest.raises(InternalError):
        await client.search("Patient")


@pytest.mark.asyncio
@respx.mock
async def test_raw_get_normalizes_leading_slash():
    respx.get(f"{BASE_URL}/metadata").mock(return_value=Response(200, json={"fhirVersion": "4.0.1"}))
    client = FHIRClient(_settings())
    result = await client.raw_get("metadata")
    assert result == {"fhirVersion": "4.0.1"}
