import time

import pytest

from app.auth.session import SessionStore
from app.utils.errors import UnauthorizedError


def test_create_and_get_session():
    store = SessionStore()
    session_id = store.create(patient_id="123", access_token="tok", refresh_token="rtok")
    session = store.get(session_id)
    assert session.patient_id == "123"
    assert session.access_token == "tok"


def test_get_unknown_session_raises():
    store = SessionStore()
    with pytest.raises(UnauthorizedError):
        store.get("does-not-exist")


def test_expired_session_raises():
    store = SessionStore()
    session_id = store.create(patient_id="123", access_token="tok", refresh_token=None)
    store._sessions[session_id].expires_at = time.time() - 1
    with pytest.raises(UnauthorizedError):
        store.get(session_id)


def test_delete_session():
    store = SessionStore()
    session_id = store.create(patient_id="123", access_token="tok", refresh_token=None)
    store.delete(session_id)
    with pytest.raises(UnauthorizedError):
        store.get(session_id)
