"""Opt-in isolation for document-rendering unit tests."""

import httpx
import pytest


@pytest.fixture
def offline_document_conversion(monkeypatch):
    """Tests must supply a fake HTTP client rather than use local/remote converters."""

    def unexpected_http_client(*args, **kwargs):
        raise AssertionError("Rendering unit tests must explicitly mock converter HTTP")

    monkeypatch.setattr(httpx, "Client", unexpected_http_client)
    monkeypatch.setattr(httpx, "AsyncClient", unexpected_http_client)
