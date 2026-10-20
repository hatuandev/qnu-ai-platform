"""Routing details are opt-in and authorized at the HTTP boundary, never by model/client JSON."""
from contextlib import contextmanager
from contextvars import ContextVar

_enabled = ContextVar('authorized_intent_debug', default=False)


@contextmanager
def intent_debug_scope(enabled: bool):
    token = _enabled.set(enabled)
    try:
        yield
    finally:
        _enabled.reset(token)


def intent_debug_enabled() -> bool:
    return _enabled.get()
