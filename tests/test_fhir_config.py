"""Tests that do not require a live FHIR server."""

import importlib

import pytest

from digital_health_mcp.fhir import config


def test_clean_base_url_variants():
    assert config._clean_base_url("https://x.org/baseR5/") == "https://x.org/baseR5"
    assert config._clean_base_url("https://x.org/baseR5") == "https://x.org/baseR5"


def test_missing_url_raises(monkeypatch):
    monkeypatch.delenv("FHIR_BASE_URL", raising=False)
    with pytest.raises(config.ConfigError):
        config.load_settings()


def test_anonymous_access_allowed(monkeypatch):
    # Unlike DHIS2, FHIR credentials are optional -- many public/test
    # servers accept anonymous access.
    monkeypatch.setenv("FHIR_BASE_URL", "https://hapi.fhir.org/baseR5")
    monkeypatch.delenv("FHIR_TOKEN", raising=False)
    monkeypatch.delenv("FHIR_USERNAME", raising=False)
    monkeypatch.delenv("FHIR_PASSWORD", raising=False)
    s = config.load_settings()
    assert not s.uses_token
    assert s.base_url == "https://hapi.fhir.org/baseR5"


def test_token_preferred(monkeypatch):
    monkeypatch.setenv("FHIR_BASE_URL", "https://x.org/fhir")
    monkeypatch.setenv("FHIR_TOKEN", "abc123")
    monkeypatch.setenv("FHIR_USERNAME", "u")
    monkeypatch.setenv("FHIR_PASSWORD", "p")
    s = config.load_settings()
    assert s.uses_token


def test_fhir_module_imports():
    mod = importlib.import_module("digital_health_mcp.fhir.client")
    assert mod.FHIR_JSON == "application/fhir+json"
