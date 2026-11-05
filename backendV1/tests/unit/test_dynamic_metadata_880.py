import copy

import pytest
from pydantic import ValidationError

from qnu.domains.knowledge.compilation.supplement import confirm
from qnu.domains.knowledge.index.query_scope import catalog_attributes, resolve
from qnu.domains.knowledge.metadata import (
    MetadataFilter,
    matches_metadata,
    merge_scope,
    scope_conflicts,
)
from qnu.domains.rag.policy import RagPolicy
from qnu.platform.errors import AppException


def unit(**attributes):
    return {"retrieval_metadata": [{"values": {"attributes": attributes}}]}


def test_scalar_types_unknown_and_same_unit_semantics():
    evidence = unit(Mã="0012", Số=12, Bật=True)
    assert matches_metadata(evidence, MetadataFilter(attributes={"Mã": "0012", "Số": 12.0}))
    assert not matches_metadata(evidence, MetadataFilter(attributes={"Mã": 12}))
    assert not matches_metadata(evidence, MetadataFilter(attributes={"Số": True}))
    assert not matches_metadata(evidence, MetadataFilter(attributes={"Bật": 1}))
    assert not matches_metadata(evidence, MetadataFilter(attributes={"Thiếu": "x"}))
    mixed = {
        "retrieval_metadata": [
            {"values": {"attributes": {"Cơ sở": "A", "Hệ": "Chính quy"}}},
            {"values": {"attributes": {"Cơ sở": "B", "Hệ": "Liên thông"}}},
        ]
    }
    assert not matches_metadata(
        mixed, MetadataFilter(attributes={"Cơ sở": "A", "Hệ": "Liên thông"})
    )


def test_nested_scope_merge_keeps_pinned_and_previous_filters():
    fixed = {"data_year": 2026, "attributes": {"Cơ sở": "A", "Bật": True}}
    previous = {"attributes": {"Hệ": "Chính quy"}}
    current = {"attributes": {"Đợt": "Bổ sung"}}
    merged = merge_scope(merge_scope(fixed, previous), current)
    assert merged == {
        "data_year": 2026,
        "attributes": {
            "Cơ sở": "A",
            "Bật": True,
            "Hệ": "Chính quy",
            "Đợt": "Bổ sung",
        },
    }
    assert not scope_conflicts(fixed, current)
    assert scope_conflicts(fixed, {"attributes": {"Bật": 1}})
    assert scope_conflicts(fixed, {"attributes": {"Cơ sở": "B"}})


def test_legacy_snapshot_has_identical_serialization():
    legacy = {
        "data_year": 2024,
        "issued_year": None,
        "effective_on": None,
        "program": None,
        "intake": None,
    }
    assert MetadataFilter.model_validate(legacy).model_dump(mode="json") == legacy
    assert RagPolicy().model_dump(mode="json")["metadata_filter"] == {
        **legacy,
        "data_year": None,
    }
    assert matches_metadata(
        {"retrieval_metadata": [{"values": {"data_year": 2024}}]}, MetadataFilter(data_year=2024)
    )
    with pytest.raises(ValidationError):
        MetadataFilter(attributes={"Số": float("nan")})


def test_catalog_keeps_types_and_numeric_equivalence():
    corpus = [unit(Mã="12"), unit(Mã=12), unit(Mã=12.0), unit(Mã=True)]
    assert catalog_attributes(corpus) == {"Mã": ["12", 12, True]}
    with pytest.raises(AppException) as error:
        resolve("Mã: 12", MetadataFilter(), corpus)
    assert error.value.code == "answer_scope_clarification_required"


def test_query_resolves_only_labeled_catalog_values():
    corpus = [unit(**{"Cơ sở": "Quy Nhơn"}), unit(**{"Cơ sở": "Gia Lai"})]
    _, scopes, _ = resolve("Học phí ở Cơ sở Quy Nhơn?", MetadataFilter(), corpus)
    assert scopes == [MetadataFilter(attributes={"Cơ sở": "Quy Nhơn"})]
    _, scopes, _ = resolve("Quy Nhơn có gì?", MetadataFilter(), corpus)
    assert scopes == [MetadataFilter()]
    for text in (
        "Cơ sở: Chưa công bố",
        "Cơ sở Chưa rõ",
        "Cơ sở Quy Nhơn và Gia Lai",
        "Cơ sở: Quy Nhơn; Cơ sở: X",
    ):
        with pytest.raises(AppException) as error:
            resolve(text, MetadataFilter(), corpus)
        assert error.value.code == "answer_scope_clarification_required"
    with pytest.raises(AppException) as error:
        resolve("Cơ sở Gia Lai", MetadataFilter(attributes={"Cơ sở": "Quy Nhơn"}), corpus)
    assert error.value.code == "answer_scope_conflict"


def test_selector_does_not_match_prefix_of_number():
    with pytest.raises(AppException) as error:
        resolve("Số lượng: 12.5", MetadataFilter(), [unit(**{"Số lượng": 12})])
    assert error.value.code == "answer_scope_clarification_required"
    _, scopes, _ = resolve("Số lượng: 12.", MetadataFilter(), [unit(**{"Số lượng": 12})])
    assert scopes == [MetadataFilter(attributes={"Số lượng": 12})]


def test_edit_cannot_change_target_or_silently_confirm_another_proposal():
    annotation = {
        "target": "section:ocr:proof",
        "values": {"attributes": {"Cơ sở": "A"}},
        "evidence": [{"citation": "ocr:proof", "quote": "Cơ sở A"}],
    }
    content = {"supplement": {"metadata": [{"id": "a" * 64, "annotation": annotation}]}}
    original = copy.deepcopy(content)
    selected = confirm(
        content,
        ["a" * 64],
        [],
        {
            "a" * 64: {
                "values": {"attributes": {"Cơ sở": "B"}},
                "quote": "Cơ sở B",
            }
        },
    )
    assert selected[0]["target"] == annotation["target"]
    assert selected[0]["evidence"][0]["citation"] == "ocr:proof"
    assert content == original
    with pytest.raises(AppException):
        confirm(content, [], [], {"a" * 64: {"values": {}, "quote": "x"}})


def test_legacy_documents_without_metadata_do_not_acquire_a_guessed_year():
    _, filters, trace = resolve("Tuyển sinh năm 2026", MetadataFilter(), [{}])
    assert filters == [MetadataFilter()]
    assert trace["filters"] == [{}]
    _, filters, _ = resolve("Năm dữ liệu 2026", MetadataFilter(), [{}])
    assert filters == [MetadataFilter(data_year=2026)]
