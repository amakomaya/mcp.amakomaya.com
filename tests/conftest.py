import os

import pytest

# Isolate tests from the developer's local .env (which may hold real FHIR
# credentials) - env vars take precedence over the .env file in
# pydantic-settings, so setting these pins every test to a known baseline.
os.environ["FHIR_BASE_URL"] = "https://fhir.test/fhir"
os.environ["FHIR_USERNAME"] = ""
os.environ["FHIR_PASSWORD"] = ""
os.environ["FHIR_TOKEN"] = ""


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from app.config.settings import get_settings
    from app.fhir.client import get_fhir_client

    get_settings.cache_clear()
    get_fhir_client.cache_clear()
    yield
    get_settings.cache_clear()
    get_fhir_client.cache_clear()
