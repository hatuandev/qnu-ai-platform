"""Report OCR technical acceptance from an isolated run; never infer live OCR quality."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

API = "tests.integration.test_ocr_processing_api::"
REVIEW = "tests.integration.test_ocr_regressions_643::"
SAFETY = "tests.integration.test_ocr_safety_643::"
TRACE = "tests.integration.test_ocr_observability_644::"
REQUIRED_CASES = {
    "upload_revision": (
        API + "test_new_generation_keeps_previous_run_and_revision",
        API + "test_old_run_stays_pinned_after_a_new_revision",
    ),
    "durable_job": (
        "tests.integration.test_ocr_queue_transport_644::test_real_queue_delivers_persisted_run_once",
        API + "test_queue_outage_leaves_a_durable_queued_run",
        API + "test_timeout_is_uncertain_and_never_retried",
        REVIEW + "test_arq_worker_startup_accepts_the_context_arq_actually_supplies",
        REVIEW + "test_reconcile_requeues_an_expired_dispatched_worker_run",
        SAFETY + "test_expired_owner_cannot_commit_after_another_worker_claims",
    ),
    "render": (
        API + "test_docx_table_keeps_spans_values_and_footnote",
        REVIEW + "test_docx_header_is_preserved_or_reported_as_missing",
    ),
    "modelops": (
        API + "test_disabled_provider_fails_with_its_own_code",
        API + "test_provider_without_ocr_capability_is_rejected",
        REVIEW + "test_ocr_runtime_blocks_output_above_registered_model_capacity",
        TRACE + "test_quota_failure_is_visible_before_any_provider_request",
    ),
    "raw_and_derived_artifacts": tuple(
        TRACE + f"test_raw_api_returns_original_bytes_even_when_processing_fails[{mode}]"
        for mode in ("ok", "invalid_layout", "truncated", "malformed")
    )
    + (TRACE + "test_failed_layout_has_failed_parse_but_successful_raw_storage",),
    "api_and_trace": (
        API + "test_cross_workspace_and_collection_are_not_reachable",
        TRACE + "test_stages_correlate_worker_and_api_without_document_content[pdf]",
        TRACE + "test_stages_correlate_worker_and_api_without_document_content[docx]",
    ),
}


def _status(case) -> str:
    if case.find("failure") is not None or case.find("error") is not None:
        return "FAIL"
    return "NOT RUN" if case.find("skipped") is not None else "PASS"


def build_report(junit: Path, receipt: Path) -> dict:
    """Require exact test identities, no duplicates, no skipped prerequisite or hidden failure."""
    xml_bytes = junit.read_bytes()
    root = ElementTree.fromstring(xml_bytes)
    cases = {}
    duplicates = []
    for case in root.iter("testcase"):
        identity = case.get("classname", "") + "::" + case.get("name", "")
        if identity in cases:
            duplicates.append(identity)
        cases[identity] = _status(case)
    isolation = json.loads(receipt.read_text(encoding="utf-8"))
    isolated = (
        bool(re.fullmatch(r"qnu_v1_test_[a-f0-9]{16}", isolation.get("database", "")))
        and isolation.get("db_dropped") is True
        and isolation.get("legacy_sentinel_preserved") is True
    )
    stages = []
    for stage, required in REQUIRED_CASES.items():
        checks = [{"test_id": key, "status": cases.get(key, "NOT RUN")} for key in required]
        status = (
            "FAIL"
            if any(c["status"] == "FAIL" for c in checks)
            else "NOT RUN"
            if any(c["status"] == "NOT RUN" for c in checks)
            else "PASS"
        )
        stages.append({"stage": stage, "status": status, "checks": checks})
    failed = [key for key, value in cases.items() if value == "FAIL"]
    status = (
        "FAIL"
        if failed or duplicates or not isolated or isolation.get("pytest_exit") != 0
        else "NOT RUN"
        if not cases or any(s["status"] != "PASS" for s in stages)
        else "PASS"
    )
    return {
        "schema_version": "qnu.ocr.acceptance/v1",
        "technical_status": status,
        "evidence_type": "synthetic_documents_loopback_mock_ocr",
        "junit_sha256": hashlib.sha256(xml_bytes).hexdigest(),
        "receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
        "isolation_verified": isolated,
        "counts": dict(Counter(cases.values())),
        "duplicate_test_ids": duplicates,
        "failed_test_ids": failed,
        "stages": stages,
        "live_nemotron": {"status": "NOT RUN", "reason": "Not established by synthetic tests."},
        "source_image_ocr_quality": {
            "status": "NOT RUN",
            "reason": "Requires separately reviewed source images, expected text and table cells.",
        },
        "compiler_approval": "NOT RUN",
    }


def markdown(report: dict) -> str:
    lines = [
        "# Nghiệm thu luồng OCR",
        "",
        f"Kỹ thuật: **{report['technical_status']}**. Tài liệu tổng hợp, provider OCR giả lập loopback.",
        "",
        "| Bước | Kết quả | Ca bắt buộc |",
        "|---|---|---|",
    ]
    for item in report["stages"]:
        passed = sum(check["status"] == "PASS" for check in item["checks"])
        lines.append(f"| {item['stage']} | {item['status']} | {passed}/{len(item['checks'])} |")
    lines.extend(
        [
            "",
            "Nemotron thật: **NOT RUN**. Chất lượng OCR so với ảnh nguồn: **NOT RUN**.",
            "Compiler/duyệt nội dung: **NOT RUN**. Kết quả kỹ thuật không phê duyệt dữ kiện.",
            "",
            "Mỗi bước chỉ PASS khi đủ ca bắt buộc; thiếu hoặc SKIP là NOT RUN.",
            "Lỗi ngoài nhóm bắt buộc hoặc ID trùng vẫn làm kết quả tổng FAIL.",
            "",
            f"JUnit SHA256: `{report['junit_sha256']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.junit, args.receipt)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.output.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"technical_status": report["technical_status"], "counts": report["counts"]}))
    return 0 if report["technical_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
