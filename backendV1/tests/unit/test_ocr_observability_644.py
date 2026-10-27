"""Telemetry must not leak payloads or turn interrupted work into success."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from qnu.domains.ocr.telemetry import observe_stage
from qnu.platform.errors import AppException


class Events:
    def __init__(self):
        self.items = []

    def info(self, event, **fields):
        self.items.append({"event": event, **fields})


def run():
    return SimpleNamespace(
        id="ocr-test",
        workspace_id="ws-test",
        collection_id="col-test",
        source_id="src-test",
        revision_id="rev-test",
        source_sha256="a" * 64,
        generation=2,
        attempt_count=3,
        config_fingerprint="b" * 64,
        provider_id="prv-test",
        requested_by="private-person",
        config={
            "prompt": "private-prompt",
            "provider": {
                "model_name": "configured-model",
                "configuration_hash": "c" * 64,
                "api_key": "private-key",
                "base_url": "https://private.endpoint",
            },
        },
    )


@pytest.mark.parametrize(
    "code,status",
    [
        ("ocr_provider_timeout", "uncertain"),
        ("ocr_layout_invalid", "failed"),
        ("bad code with private text", "failed"),
    ],
)
def test_stage_reports_error_without_serializing_exception_or_config(code, status):
    events = Events()
    with (
        pytest.raises(AppException),
        observe_stage(run(), "ocr_page", logger=events, page_number=1),
    ):
        raise AppException("private-response", code=code)
    finished = events.items[-1]
    assert finished["status"] == status
    assert finished["duration_ms"] >= 0
    serialized = json.dumps(events.items)
    assert "private" not in serialized
    assert "bad code" not in serialized
    assert finished["attempt"] == 3 and finished["generation"] == 2


def test_cancellation_is_recorded_and_propagated():
    events = Events()
    with pytest.raises(asyncio.CancelledError), observe_stage(run(), "render", logger=events):
        raise asyncio.CancelledError()
    assert events.items[-1]["status"] == "cancelled"
    assert events.items[-1]["error_code"] == "processing_interrupted"


def test_missing_usage_remains_unknown():
    events = Events()
    with observe_stage(run(), "ocr_page", logger=events):
        pass
    assert "usage_tokens" not in events.items[-1]
