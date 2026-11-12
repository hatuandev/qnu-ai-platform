"""Scoped image-OCR warnings and the human acknowledgement bound to them.

Only failures local to one supplementary image may become warnings. Provider-wide,
timeout, auth or quota errors stay fatal for the run.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable
from typing import Any

from qnu.platform.errors import AppException

LOCAL_IMAGE_FAILURE_CODES = frozenset(
    {"embedded_image_decode_failed", "ocr_provider_rejected", "mineru_pdf_required"}
)

MAX_IMAGE_FAILURES = 2048
MAX_ERROR_CODE_LENGTH = 64


def failure_record(
    asset_no: int, page: int, bbox: object, code: str, attempts: int
) -> dict[str, Any]:
    return {
        "image_asset_no": int(asset_no),
        "page": int(page),
        "bbox": [float(value) for value in bbox] if bbox is not None else None,
        "error_code": code,
        "attempts": int(attempts),
    }


def image_failures_fingerprint(failures: Iterable[dict[str, Any]]) -> str:
    payload = json.dumps(
        list(failures), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def acknowledged(
    config: dict[str, Any] | None, failures: Iterable[dict[str, Any]]
) -> dict[str, Any] | None:
    entries = list(failures)
    if not entries:
        return None
    ack = (config or {}).get("image_ocr_ack")
    if not isinstance(ack, dict):
        return None
    return ack if ack.get("fingerprint") == image_failures_fingerprint(entries) else None


def normalize_failures(value: object, page: int) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_IMAGE_FAILURES:
        raise _invalid()
    records: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise _invalid()
        asset, bbox = item.get("image_asset_no"), item.get("bbox")
        code, attempts = item.get("error_code"), item.get("attempts")
        if (
            type(asset) is not int
            or asset <= 0
            or not isinstance(code, str)
            or not 0 < len(code) <= MAX_ERROR_CODE_LENGTH
            or type(attempts) is not int
            or attempts < 1
            or item.get("page") != page
            or (
                bbox is not None
                and (
                    not isinstance(bbox, list)
                    or len(bbox) != 4
                    or not all(type(value) in (int, float) and math.isfinite(value) for value in bbox)
                    or not 0 <= bbox[0] < bbox[2] <= 1
                    or not 0 <= bbox[1] < bbox[3] <= 1
                )
            )
        ):
            raise _invalid()
        records.append(failure_record(asset, page, bbox, code, attempts))
    return records


def _invalid() -> AppException:
    return AppException(
        "Bản ghi cảnh báo ảnh OCR không hợp lệ.",
        code="ocr_response_invalid",
        status_code=502,
        title="Phản hồi OCR không hợp lệ",
    )


__all__ = [
    "LOCAL_IMAGE_FAILURE_CODES",
    "acknowledged",
    "failure_record",
    "image_failures_fingerprint",
    "normalize_failures",
]
