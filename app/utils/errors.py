"""
Friendly, user-safe error handling.

Rule: Claude / the end user must never see a raw stack trace, SQL error,
or internal exception message. Every failure is translated into one of the
AppError subclasses below with a short, friendly message.
"""
from __future__ import annotations


class AppError(Exception):
    """Base class for all errors that are safe to show to the user."""

    status_code: int = 500
    friendly_message: str = "Something went wrong. Please try again shortly."

    def __init__(self, friendly_message: str | None = None) -> None:
        if friendly_message:
            self.friendly_message = friendly_message
        super().__init__(self.friendly_message)


class UnauthorizedError(AppError):
    status_code = 401
    friendly_message = "You need to sign in again to continue."


class ForbiddenError(AppError):
    status_code = 403
    friendly_message = "You don't have permission to access that information."


class NotFoundError(AppError):
    status_code = 404
    friendly_message = "We couldn't find that information."


class TimeoutErrorApp(AppError):
    status_code = 408
    friendly_message = "The health records system is taking too long to respond. Please try again."


class InternalError(AppError):
    status_code = 500
    friendly_message = "Something went wrong on our end. Please try again shortly."


def to_friendly(exc: Exception) -> AppError:
    """Convert any exception into a safe, user-facing AppError."""
    if isinstance(exc, AppError):
        return exc
    return InternalError()
