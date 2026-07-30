"""Tests for Keycloak login and access-token validation. No live Keycloak
needed -- JWKS lookup and the token endpoint are monkeypatched."""

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from digital_health_mcp.fhir import auth

ISSUER = "https://keycloak.example.com/realms/amakomaya"


@pytest.fixture(autouse=True)
def base_env(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_ISSUER", ISSUER)
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "amakomaya-mcp")
    monkeypatch.delenv("KEYCLOAK_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("KEYCLOAK_AUDIENCE", raising=False)


@pytest.fixture
def keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _sign(private_key, claims: dict) -> str:
    return jwt.encode(claims, private_key, algorithm="RS256")


def _patch_jwks(monkeypatch, public_key):
    class FakeSigningKey:
        key = public_key

    class FakeJWKClient:
        def get_signing_key_from_jwt(self, token):
            return FakeSigningKey()

    monkeypatch.setattr(auth, "_jwk_client", lambda url: FakeJWKClient())


def test_missing_issuer_raises(monkeypatch):
    monkeypatch.delenv("KEYCLOAK_ISSUER", raising=False)
    with pytest.raises(auth.ConfigError):
        auth.load_settings()


def test_missing_client_id_raises(monkeypatch):
    monkeypatch.delenv("KEYCLOAK_CLIENT_ID", raising=False)
    with pytest.raises(auth.ConfigError):
        auth.load_settings()


def test_urls_default_from_issuer():
    s = auth.load_settings()
    assert s.jwks_url == f"{ISSUER}/protocol/openid-connect/certs"
    assert s.token_url == f"{ISSUER}/protocol/openid-connect/token"


def test_extract_preferred_username(monkeypatch, keypair):
    private_key, public_key = keypair
    _patch_jwks(monkeypatch, public_key)

    token = _sign(private_key, {"preferred_username": "9841234567", "iss": ISSUER})

    assert auth.extract_preferred_username(token) == "9841234567"


def test_wrong_issuer_rejected(monkeypatch, keypair):
    private_key, public_key = keypair
    _patch_jwks(monkeypatch, public_key)

    token = _sign(
        private_key,
        {"preferred_username": "9841234567", "iss": "https://not-our-realm.example"},
    )

    with pytest.raises(auth.KeycloakError):
        auth.extract_preferred_username(token)


def test_missing_preferred_username_claim_raises(monkeypatch, keypair):
    private_key, public_key = keypair
    _patch_jwks(monkeypatch, public_key)

    token = _sign(private_key, {"iss": ISSUER, "sub": "abc-123"})

    with pytest.raises(auth.KeycloakError):
        auth.extract_preferred_username(token)


def test_empty_token_rejected():
    with pytest.raises(auth.KeycloakError):
        auth.extract_preferred_username("")


def test_login_with_password_success(monkeypatch, keypair):
    private_key, public_key = keypair
    _patch_jwks(monkeypatch, public_key)
    token = _sign(private_key, {"preferred_username": "9841234567", "iss": ISSUER})

    def fake_post(url, data, timeout, verify):
        assert url == f"{ISSUER}/protocol/openid-connect/token"
        assert data["grant_type"] == "password"
        assert data["username"] == "9841234567"
        assert data["password"] == "correct-horse"
        return httpx.Response(200, json={"access_token": token})

    monkeypatch.setattr(auth.httpx, "post", fake_post)

    username = auth.login_with_password("9841234567", "correct-horse")
    assert username == "9841234567"


def test_login_with_password_wrong_credentials(monkeypatch):
    def fake_post(url, data, timeout, verify):
        return httpx.Response(401, json={"error": "invalid_grant"})

    monkeypatch.setattr(auth.httpx, "post", fake_post)

    with pytest.raises(auth.KeycloakError):
        auth.login_with_password("9841234567", "wrong-password")


def test_login_with_password_requires_credentials():
    with pytest.raises(auth.KeycloakError):
        auth.login_with_password("", "")
