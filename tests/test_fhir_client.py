import pytest
import respx
from httpx import Response

from app.fhir.client import FHIRClient
from app.utils.errors import ForbiddenError, NotFoundError, TimeoutErrorApp, UnauthorizedError


@pytest.mark.asyncio
@respx.mock
async def test_search_success():
    respx.get("https://fhir.test/fhir/Appointment").mock(
        return_value=Response(200, json={"entry": []})
    )
    client = FHIRClient(access_token="fake-token")
    result = await client.search("Appointment", params={"patient": "Patient/1"})
    assert result == {"entry": []}


@pytest.mark.asyncio
@respx.mock
async def test_search_unauthorized():
    respx.get("https://fhir.test/fhir/Appointment").mock(return_value=Response(401))
    client = FHIRClient(access_token="bad-token")
    with pytest.raises(UnauthorizedError):
        await client.search("Appointment")


@pytest.mark.asyncio
@respx.mock
async def test_search_forbidden():
    respx.get("https://fhir.test/fhir/Appointment").mock(return_value=Response(403))
    client = FHIRClient(access_token="token")
    with pytest.raises(ForbiddenError):
        await client.search("Appointment")


@pytest.mark.asyncio
@respx.mock
async def test_search_not_found():
    respx.get("https://fhir.test/fhir/Appointment").mock(return_value=Response(404))
    client = FHIRClient(access_token="token")
    with pytest.raises(NotFoundError):
        await client.search("Appointment")


@pytest.mark.asyncio
@respx.mock
async def test_search_timeout():
    import httpx
    respx.get("https://fhir.test/fhir/Appointment").mock(side_effect=httpx.TimeoutException("timeout"))
    client = FHIRClient(access_token="token")
    with pytest.raises(TimeoutErrorApp):
        await client.search("Appointment")
