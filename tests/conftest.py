import os

import pytest

# Provide minimal required env vars so Settings() can be instantiated
# during tests without a real .env file.
os.environ.setdefault("KEYCLOAK_URL", "https://auth.test")
os.environ.setdefault("KEYCLOAK_REALM", "test-realm")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "test-client")
os.environ.setdefault("FHIR_BASE_URL", "https://fhir.test/fhir")


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from app.config.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
