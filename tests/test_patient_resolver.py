import pytest
import respx
from httpx import Response

from app.fhir.patient_resolver import resolve_patient_id
from app.utils.errors import PatientIdentityConflictError, PatientNotFoundError


@pytest.mark.asyncio
@respx.mock
async def test_resolve_patient_id_success():
    respx.get("https://fhir.test/fhir/Patient").mock(
        return_value=Response(200, json={
            "entry": [{"resource": {"id": "12345", "resourceType": "Patient"}}]
        })
    )
    patient_id = await resolve_patient_id("jane.doe")
    assert patient_id == "12345"


@pytest.mark.asyncio
@respx.mock
async def test_resolve_patient_id_not_found():
    respx.get("https://fhir.test/fhir/Patient").mock(
        return_value=Response(200, json={"entry": []})
    )
    with pytest.raises(PatientNotFoundError):
        await resolve_patient_id("unknown.user")


@pytest.mark.asyncio
@respx.mock
async def test_resolve_patient_id_conflict():
    respx.get("https://fhir.test/fhir/Patient").mock(
        return_value=Response(200, json={
            "entry": [
                {"resource": {"id": "1"}},
                {"resource": {"id": "2"}},
            ]
        })
    )
    with pytest.raises(PatientIdentityConflictError):
        await resolve_patient_id("duplicate.user")
