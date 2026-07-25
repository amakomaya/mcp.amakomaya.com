from app.utils.errors import AppError, InternalError, UnauthorizedError, to_friendly


def test_app_error_defaults():
    err = UnauthorizedError()
    assert err.status_code == 401
    assert "sign in" in err.friendly_message.lower()


def test_custom_message_overrides_default():
    err = UnauthorizedError("Custom message")
    assert err.friendly_message == "Custom message"


def test_to_friendly_wraps_unknown_exceptions():
    friendly = to_friendly(ValueError("some internal detail"))
    assert isinstance(friendly, InternalError)
    assert "internal detail" not in friendly.friendly_message
