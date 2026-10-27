"""Redaction must mask credentials before they reach logs."""

from __future__ import annotations

from qnu.platform.redaction import redact


def test_redacts_bearer_and_api_keys() -> None:
    text = "call failed: Bearer abc.def.ghi key sk-live-1234567890"
    cleaned = redact(text)
    assert "abc.def.ghi" not in cleaned
    assert "sk-live" not in cleaned


def test_redacts_email_and_phone() -> None:
    cleaned = redact("lien he admin@qnu.edu.vn hoac 0912345678")
    assert "admin@qnu.edu.vn" not in cleaned
    assert "0912345678" not in cleaned
