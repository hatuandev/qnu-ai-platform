"""Failure semantics shared by the OCR run and its adapters.

A timeout means the request reached the provider but no usable answer came back. That
is not a failure to retry: retrying could bill the same page twice, so the run records
``uncertain`` and stops. Everything else is a known outcome with its own code.
"""

from __future__ import annotations

UNCERTAIN_CODES = frozenset({"ocr_provider_timeout"})


def is_uncertain(code: str) -> bool:
    return code in UNCERTAIN_CODES


__all__ = ["UNCERTAIN_CODES", "is_uncertain"]
