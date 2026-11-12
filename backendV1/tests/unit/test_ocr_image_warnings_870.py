"""Image-OCR warning records, fingerprint binding and malformed-record rejection."""

import pytest

from qnu.domains.ocr.warnings import (
    acknowledged,
    failure_record,
    image_failures_fingerprint,
    normalize_failures,
)
from qnu.platform.errors import AppException


def test_fingerprint_binds_the_exact_failure_list_to_one_acknowledgement():
    failures = [
        failure_record(10001, 1, [0.1, 0.2, 0.3, 0.4], "ocr_provider_rejected", 1),
        failure_record(10002, 2, None, "embedded_image_decode_failed", 2),
    ]
    config = {
        "image_ocr_ack": {
            "fingerprint": image_failures_fingerprint(failures),
            "by": "actor",
            "images_failed": 2,
        }
    }
    assert acknowledged(config, failures) == config["image_ocr_ack"]
    assert acknowledged(config, failures[:1]) is None
    assert acknowledged(config, list(reversed(failures))) is None
    assert acknowledged({"image_ocr_ack": {"fingerprint": "stale"}}, failures) is None


def test_failure_record_writes_stable_numeric_fields():
    record = failure_record(7, 3, (0, 0.5, 1, 1), "ocr_provider_rejected", 1)
    assert record == {
        "image_asset_no": 7,
        "page": 3,
        "bbox": [0.0, 0.5, 1.0, 1.0],
        "error_code": "ocr_provider_rejected",
        "attempts": 1,
    }


@pytest.mark.parametrize(
    "record",
    [
        {"image_asset_no": 0, "page": 1, "bbox": None, "error_code": "x", "attempts": 1},
        {"image_asset_no": 1, "page": 2, "bbox": None, "error_code": "x", "attempts": 1},
        {
            "image_asset_no": 1,
            "page": 1,
            "bbox": [0.5, 0, 0.4, 1],
            "error_code": "x",
            "attempts": 1,
        },
        {"image_asset_no": 1, "page": 1, "bbox": None, "error_code": "", "attempts": 1},
        {"image_asset_no": 1, "page": 1, "bbox": None, "error_code": "x", "attempts": 0},
        {"image_asset_no": 1, "page": 1, "bbox": None, "error_code": "x"},
    ],
)
def test_malformed_or_unbound_records_are_rejected(record):
    with pytest.raises(AppException) as exc:
        normalize_failures([record], 1)
    assert exc.value.code == "ocr_response_invalid"


def test_valid_record_without_bbox_round_trips():
    record = failure_record(5, 1, None, "mineru_pdf_required", 1)
    assert normalize_failures([record], 1) == [record]
