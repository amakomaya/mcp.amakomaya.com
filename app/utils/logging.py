"""
Structured logging.

Never log:
  - access tokens / refresh tokens
  - patient data or clinical notes
  - any raw JWT

Always safe to log:
  - request id
  - tool name
  - execution time
  - http status code
"""
from __future__ import annotations

import logging
import sys
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar

from app.config.settings import get_settings

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get()
        return True


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | request_id=%(request_id)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def new_request_id() -> str:
    request_id = uuid.uuid4().hex[:12]
    _request_id_ctx.set(request_id)
    return request_id


@contextmanager
def log_tool_call(tool_name: str):
    """
    Wrap an MCP tool call to log: tool name, execution time, and outcome
    status - never the arguments or the returned patient data.
    """
    logger = get_logger("amakomaya.tools")
    start = time.perf_counter()
    status = "ok"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "tool_call tool=%s status=%s duration_ms=%.1f",
            tool_name,
            status,
            elapsed_ms,
        )
