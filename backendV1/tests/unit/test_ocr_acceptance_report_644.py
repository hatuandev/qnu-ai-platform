"""A report must never silently omit missing, skipped, failed or duplicate evidence."""

import json
from xml.etree import ElementTree

import pytest

from scripts.ocr_acceptance_report import REQUIRED_CASES, build_report


def evidence(tmp_path, *, omitted=None, skipped=None, failed=None, duplicate=None, isolated=True):
    suite = ElementTree.Element("testsuite")
    identities = list(dict.fromkeys(key for values in REQUIRED_CASES.values() for key in values))
    if failed == "outside":
        identities.append("tests.unit.other::unexpected_failure")
        failed = identities[-1]
    for key in identities:
        if key == omitted:
            continue
        module, name = key.split("::")
        case = ElementTree.SubElement(suite, "testcase", classname=module, name=name)
        if key == skipped:
            ElementTree.SubElement(case, "skipped")
        if key == failed:
            ElementTree.SubElement(case, "failure")
        if key == duplicate:
            ElementTree.SubElement(suite, "testcase", classname=module, name=name)
    xml_path = tmp_path / "result.xml"
    ElementTree.ElementTree(suite).write(xml_path, encoding="utf-8")
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "database": "qnu_v1_test_" + "a" * 16,
                "db_dropped": isolated,
                "legacy_sentinel_preserved": True,
                "pytest_exit": 1 if failed else 0,
            }
        )
    )
    return build_report(xml_path, receipt)


def test_complete_technical_evidence_never_claims_live_ocr_quality(tmp_path):
    report = evidence(tmp_path)
    assert report["technical_status"] == "PASS"
    assert report["live_nemotron"]["status"] == "NOT RUN"
    assert report["source_image_ocr_quality"]["status"] == "NOT RUN"
    assert report["compiler_approval"] == "NOT RUN"


@pytest.mark.parametrize(
    "change,status",
    [
        ("omitted", "NOT RUN"),
        ("skipped", "NOT RUN"),
        ("failed", "FAIL"),
        ("duplicate", "FAIL"),
    ],
)
def test_incomplete_or_invalid_evidence_cannot_pass(tmp_path, change, status):
    required = next(iter(REQUIRED_CASES.values()))[0]
    assert evidence(tmp_path, **{change: required})["technical_status"] == status


def test_failure_outside_required_cases_is_not_hidden(tmp_path):
    assert evidence(tmp_path, failed="outside")["technical_status"] == "FAIL"


def test_unconfirmed_database_cleanup_cannot_pass(tmp_path):
    assert evidence(tmp_path, isolated=False)["technical_status"] == "FAIL"
