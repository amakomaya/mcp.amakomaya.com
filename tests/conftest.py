import os

import pytest

# Provide minimal required env vars so Settings() can be instantiated
# during tests without a real .env file.
os.environ.setdefault("FHIR_BASE_URL", "https://fhir.test/fhir")


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from app.config.settings import get_settings
    from app.fhir.client import get_fhir_client

    get_settings.cache_clear()
    get_fhir_client.cache_clear()
    yield
    get_settings.cache_clear()
    get_fhir_client.cache_clear()
