"""Unit tests for Phase 2 Slice 5: Confusable siblings detection."""

from __future__ import annotations

from qnu.domains.rag.answer.confusable_siblings import (
    are_digit_permutations,
    build_confusable_warning,
    find_confusable_siblings,
    levenshtein_distance,
    scan_for_confusables,
)
from qnu.domains.rag.answer.schemas import EvidenceSource


def test_levenshtein_distance_cases():
    assert levenshtein_distance("7480201", "7480201") == 0
    assert levenshtein_distance("7480201", "7480202") == 1
    assert levenshtein_distance("AM-0007", "AM-0070") == 2
    assert levenshtein_distance("0012", "0120") == 2
    assert levenshtein_distance("0012", "9999") == 4


def test_transposition_detection():
    assert are_digit_permutations("0012", "0120") is True
    assert are_digit_permutations("12", "21") is True
    assert are_digit_permutations("0012", "0013") is False
    assert are_digit_permutations("0012", "0012") is False


def test_find_confusable_siblings_detection():
    candidates = ["0120", "0013", "0014", "9999", "0012"]
    siblings = find_confusable_siblings("0012", candidates)
    # Both transposed '0120' and dist=1 '0013' must be detected
    assert "0120" in siblings
    assert "0013" in siblings
    assert "9999" not in siblings
    assert "0012" not in siblings  # Exclude self


def test_find_confusable_siblings_major_codes():
    candidates = ["AM-0070", "AM-0008", "KT-9999"]
    siblings = find_confusable_siblings("AM-0007", candidates)
    assert "AM-0070" in siblings
    assert "KT-9999" not in siblings


def test_build_confusable_warning_output():
    warning = build_confusable_warning("0012", ["0120"])
    assert "[CẢNH BÁO ĐỊNH DANH]" in warning
    assert "'0012'" in warning
    assert "'0120'" in warning
    assert "Tuyệt đối KHÔNG trộn lẫn" in warning


def test_scan_for_confusables_integration():
    source = EvidenceSource(
        evidence_id="E1",
        chunk_id="ich_1",
        document_id="cdoc_1",
        version_id="cver_1",
        publication_decision_id="pdec_1",
        score=1.0,
        kind="paragraph",
        text="Thí sinh thuộc nhóm 0120 được hưởng ưu tiên khu vực 1.",
        citations={},
        structure={},
    )
    # User asks about code 0012, source mentions confusable 0120
    query = "Hồ sơ mã 0012 có được ưu tiên khu vực không?"
    results = scan_for_confusables(query, [source])
    assert len(results) == 1
    assert results[0]["target_code"] == "0012"
    assert "0120" in results[0]["siblings"]
    assert "[CẢNH BÁO ĐỊNH DANH]" in results[0]["warning"]
