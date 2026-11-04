"""Scope, provenance, context relationships and statement verification contracts."""

import json

import pytest
from pydantic import ValidationError

from qnu.domains.assistants.schemas import AssistantConfig, AssistantCreate
from qnu.domains.knowledge.index.chunking import build_chunks
from qnu.domains.knowledge.metadata import (
    MetadataFilter,
    RetrievalAnnotation,
    chunk_metadata,
    matches_metadata,
    validate_annotations,
)
from qnu.domains.rag.answer.schemas import EvidenceSource, Statement
from qnu.domains.rag.answer.verification import parse_report
from qnu.domains.rag.policy import RagPolicy
from qnu.platform.errors import AppException
from tests.unit.test_index_chunking_647 import fixture


def annotation(target="paragraph:0:0", year=2024):
    return {
        "target": target,
        "values": {"data_year": year},
        "evidence": [{"citation": "ocr-example:ev-table", "quote": str(year)}],
    }


def test_old_policy_is_compatible_and_new_policy_is_explicit():
    old = RagPolicy.model_validate({})
    assert old.verification_max_output_tokens is None
    assert RagPolicy(verification_max_output_tokens=32768).verification_max_output_tokens == 32768
    assert (
        old.retrieval_mode == "dense" and old.context_window == 0 and old.verification_mode == "off"
    )
    config = AssistantCreate(
        name="Test",
        collection_id="collection",
        rag_policy={"retrieval_mode": "hybrid", "candidate_k": 10},
    )
    assert config.rag_policy.candidate_k == 10
    assert config.rag_policy.context_window == 1


@pytest.mark.parametrize(
    "policy",
    [
        {"rerank_provider_id": "p"},
        {"verification_provider_id": "p"},
        {"context_window": 6},
        {"candidate_k": 0},
        {"metadata_filter": {"year": 2024}},
    ],
)
def test_invalid_policy_is_rejected(policy):
    with pytest.raises(ValidationError):
        RagPolicy.model_validate(policy)


def test_hybrid_candidate_budget_is_validated_at_assistant_boundary():
    with pytest.raises(ValidationError):
        AssistantConfig(
            name="Test",
            collection_id="c",
            top_k=5,
            rag_policy={"retrieval_mode": "hybrid", "candidate_k": 4},
        )


def test_metadata_never_infers_data_year_from_document_metadata():
    with pytest.raises(ValidationError):
        RetrievalAnnotation.model_validate(annotation("document"))
    assert not matches_metadata(
        {"retrieval_metadata": [{"values": {"issued_year": 2024}}]}, MetadataFilter(data_year=2024)
    )
    assert not matches_metadata(None, MetadataFilter(data_year=2024))


def test_global_metadata_proof_is_retained_on_its_own_and_when_inherited():
    common = {
        "target": "document",
        "values": {"issued_year": 2023},
        "evidence": [{"citation": "ocr:date", "quote": "2023"}],
    }
    local = annotation()
    only_global = chunk_metadata([common], {"paragraph:0:0"})
    assert only_global[0]["evidence"] == common["evidence"]
    combined = chunk_metadata([common, local], {"paragraph:0:0"})
    assert combined[0]["values"] == {"issued_year": 2023, "data_year": 2024}
    assert combined[0]["evidence"] == [*common["evidence"], *local["evidence"]]


def test_composite_documents_cannot_inherit_global_metadata_from_one_source():
    content, documents = fixture()
    common = {
        "target": "document",
        "values": {"issued_year": 2024},
        "evidence": [{"citation": "ocr-example:ev-table", "quote": "2024"}],
    }
    with pytest.raises(AppException) as error:
        validate_annotations([common], content, [*documents, *documents])
    assert error.value.code == "retrieval_metadata_invalid"


def test_combined_scope_must_match_one_annotated_unit():
    structure = {
        "retrieval_metadata": [
            {"values": {"data_year": 2024, "program": "A"}},
            {"values": {"data_year": 2025, "program": "B"}},
        ]
    }
    assert matches_metadata(structure, MetadataFilter(data_year=2024, program="A"))
    assert not matches_metadata(structure, MetadataFilter(data_year=2024, program="B"))


def test_effective_filter_requires_both_known_boundaries():
    scope = MetadataFilter(effective_on="2024-07-01")
    assert not matches_metadata(
        {"retrieval_metadata": [{"values": {"effective_from": "2024-01-01"}}]}, scope
    )
    assert matches_metadata(
        {
            "retrieval_metadata": [
                {"values": {"effective_from": "2024-01-01", "effective_until": "2024-12-31"}}
            ]
        },
        scope,
    )


@pytest.mark.parametrize(
    "target",
    [
        "paragraph:99:0",
        "table:ocr-example:ev-table:row:99",
        "table:ocr-example:ev-table:row:1:column:99",
        "anything",
    ],
)
def test_annotation_target_must_exist(target):
    content, documents = fixture()
    with pytest.raises(AppException, match=".*"):
        validate_annotations([annotation(target)], content, documents)


def test_paragraph_relationships_are_stable_and_do_not_use_global_ordinal():
    content, documents = fixture()
    content["sections"][0]["paragraphs"] *= 2
    content["sections"] += [
        {"heading": "Other", "paragraphs": content["sections"][0]["paragraphs"][:1]}
    ]
    paragraphs = [c for c in build_chunks(content, documents, 1800) if c.kind == "paragraph"]
    assert (
        paragraphs[0].structure["context"]["parent"] == paragraphs[1].structure["context"]["parent"]
    )
    assert (
        paragraphs[2].structure["context"]["parent"] != paragraphs[0].structure["context"]["parent"]
    )


def test_cell_annotations_do_not_leak_to_unselected_table_fragments():
    content, documents = fixture(20)
    item = annotation("table:ocr-example:ev-table:row:19:column:2")
    chunks = build_chunks(content, documents, 1800, [item])
    matching = [c for c in chunks if matches_metadata(c.structure, MetadataFilter(data_year=2024))]
    assert matching and all(19 in c.structure["row_indices"] for c in matching)
    assert any(
        c.kind == "table" and not matches_metadata(c.structure, MetadataFilter(data_year=2024))
        for c in chunks
    )


def source():
    return EvidenceSource(
        evidence_id="E1",
        chunk_id="c",
        document_id="d",
        version_id="v",
        publication_decision_id="p",
        score=1,
        kind="paragraph",
        text="Năm 2024 có 100 chỉ tiêu.",
        citations={},
        structure=None,
    )


def report(status="supported", quote="Năm 2024 có 100 chỉ tiêu.", index=0):
    return {
        "findings": [
            {
                "statement_index": index,
                "status": status,
                "reason": "Đối chiếu trực tiếp.",
                "quotes": [{"evidence_id": "E1", "quote": quote}],
            }
        ]
    }


def test_supported_report_requires_resolving_quotes_and_numeric_support():
    statements = [Statement(text="Năm 2024 có 100 chỉ tiêu.", evidence_ids=["E1"])]
    assert (
        parse_report(json.dumps(report()), statements, [source()]).findings[0].status == "supported"
    )
    statements[0].text = "Năm 2024 có 900 chỉ tiêu."
    assert (
        parse_report(json.dumps(report()), statements, [source()]).findings[0].status == "uncertain"
    )


@pytest.mark.parametrize(
    "case", ["missing", "duplicate", "foreign_id", "invented_quote", "no_quotes", "wrong_index"]
)
def test_judge_cannot_self_validate_invented_or_incomplete_evidence(case):
    value = report()
    finding = value["findings"][0]
    if case == "missing":
        value["findings"] = []
    if case == "duplicate":
        value["findings"] *= 2
    if case == "foreign_id":
        finding["quotes"][0]["evidence_id"] = "E2"
    if case == "invented_quote":
        finding["quotes"][0]["quote"] = "900"
    if case == "no_quotes":
        finding["quotes"] = []
    if case == "wrong_index":
        finding["statement_index"] = 1
    with pytest.raises(AppException) as error:
        parse_report(
            json.dumps(value), [Statement(text="100 chỉ tiêu.", evidence_ids=["E1"])], [source()]
        )
    assert error.value.code == "answer_verification_invalid"
