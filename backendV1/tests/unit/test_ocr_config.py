"""Pinned run configuration: the fingerprint must change with anything that can change bytes."""

from __future__ import annotations

import pytest

from qnu.domains.ocr.config import (
    ProcessingConfig,
    config_from_run,
    config_payload,
    processing_config,
)
from qnu.platform.config import Settings
from qnu.platform.errors import AppException

BASE = ProcessingConfig(
    dpi=144,
    max_pages=300,
    max_page_bytes=8 * 1024 * 1024,
    max_output_tokens=8192,
    prompt_version="nemotron-parse/v1",
    processor_version="qnu-ocr/v1",
    table_layout_version="nemotron-tabular/v1",
)


def test_fingerprint_is_stable_for_the_same_config() -> None:
    assert BASE.fingerprint == processing_config(Settings()).fingerprint


@pytest.mark.parametrize(
    "change",
    [
        {"dpi": 200},
        {"max_pages": 10},
        {"max_page_bytes": 1024},
        {"max_output_tokens": 4096},
        {"prompt_version": "nemotron-parse/v2"},
        {"processor_version": "qnu-ocr/v2"},
        {"table_layout_version": "nemotron-tabular/v2"},
    ],
)
def test_fingerprint_changes_with_any_byte_shaping_setting(change: dict) -> None:
    changed = ProcessingConfig(**{**BASE.as_dict(), **change})
    assert changed.fingerprint != BASE.fingerprint


def test_payload_round_trips_through_a_stored_run() -> None:
    payload = config_payload(BASE)
    assert config_from_run(payload) == BASE
    assert payload["provider"] is None


def test_a_stored_run_without_the_pinned_keys_is_rejected() -> None:
    payload = config_payload(BASE)
    payload["renderer"].pop("max_pages")
    with pytest.raises(AppException) as caught:
        config_from_run(payload)
    assert caught.value.code == "processing_config_invalid"
    assert caught.value.status_code == 409


def test_a_stored_run_never_falls_back_to_todays_defaults() -> None:
    # A run pinned at 72 dpi must replay at 72 dpi, whatever the current settings say.
    stored = config_payload(ProcessingConfig(**{**BASE.as_dict(), "dpi": 72}))
    assert config_from_run(stored).dpi == 72
