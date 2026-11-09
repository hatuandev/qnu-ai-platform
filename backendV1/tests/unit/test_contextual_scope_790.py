"""Held-out synthetic policies: source binding, ambiguous scope and sealed enrichment."""

import copy
from types import SimpleNamespace

import pytest

from qnu.domains.knowledge.index.chunking import build_chunks
from qnu.domains.knowledge.index.contextual import enrich, glossary, original_text
from qnu.domains.knowledge.index.query_scope import resolve, result_scopes
from qnu.domains.knowledge.metadata import MetadataFilter, validate_annotations
from qnu.domains.rag.answer.projection import evidence_item
from qnu.platform.errors import AppException
from tests.unit.test_index_chunking_647 import fixture


def scoped(program="Hải dương học", intake="Đợt A", year=2031, **extra):
    return {
        "retrieval_metadata": [
            {
                "target": "paragraph:0:0",
                "values": {
                    "program": program,
                    "intake": intake,
                    "data_year": year,
                    **extra,
                },
                "evidence": [{"citation": "ocr:proof", "quote": f"{program} {intake} {year}"}],
            }
        ]
    }


def test_proof_from_another_block_in_same_file_cannot_annotate_paragraph():
    content, docs = fixture()
    docs[0]["pages"][0]["blocks"].append({"evidence_id": "ev-text", "text": "Chưa rõ năm."})
    proof = {
        "target": "paragraph:0:0",
        "values": {"data_year": 2031},
        "evidence": [
            {"citation": "ocr-example:ev-note", "quote": "2031"},
        ],
    }
    docs[0]["pages"][0]["blocks"][1]["text"] = "2031"
    with pytest.raises(AppException, match="target"):
        validate_annotations([proof], content, docs)


@pytest.mark.parametrize("target", ["row:1", "row:1:column:2"])
def test_table_wide_quote_cannot_assign_another_rows_metadata(target):
    content, docs = fixture()
    docs[0]["pages"][0]["blocks"][0].update(text="2031", table=content["source_tables"][0]["table"])
    proof = {
        "target": "table:ocr-example:ev-table:" + target,
        "values": {"data_year": 2031},
        "evidence": [
            {"citation": "ocr-example:ev-table", "quote": "2031"},
        ],
    }
    with pytest.raises(AppException, match="target"):
        validate_annotations([proof], content, docs)


def test_valid_cell_proof_and_unknown_title_year_are_preserved():
    content, docs = fixture()
    docs[0]["pages"][0]["blocks"][0]["table"] = content["source_tables"][0]["table"]
    proof = {
        "target": "table:ocr-example:ev-table:row:0:column:2",
        "values": {"data_year": 2024},
        "evidence": [
            {"citation": "ocr-example:ev-cell-0-2", "quote": "2024"},
        ],
    }
    validate_annotations([proof], content, docs)
    content["title"] = "Thông báo 2099"
    chunks = build_chunks(content, docs, 6000, [proof])
    enriched = enrich(chunks, content, docs, 10000)
    assert not enriched[0].structure["retrieval_metadata"]
    assert "2099" not in str(enriched[1].structure["retrieval_metadata"])
    assert all(original_text(c) == old.text for c, old in zip(enriched, chunks, strict=True))


def test_table_proof_cannot_use_a_quote_synthesized_by_joining_cells():
    content, docs = fixture()
    docs[0]["pages"][0]["blocks"][0].update(
        table=content["source_tables"][0]["table"],
        text="Chỉ tiêu | 2023 | 2024",
    )
    proof = {
        "target": "table:ocr-example:ev-table:row:0",
        "values": {"data_year": 2024},
        "evidence": [
            {"citation": "ocr-example:ev-table", "quote": "2023\n2024"},
        ],
    }
    with pytest.raises(AppException):
        validate_annotations([proof], content, docs)


def test_catalog_resolves_explicit_scope_and_never_guesses_unknown_year():
    corpus = [scoped(), scoped(program="Khí tượng học", year=2032)]
    _, filters, trace = resolve("Hải dương học năm 2031", MetadataFilter(), corpus)
    assert filters == [MetadataFilter(program="Hải dương học", data_year=2031)]
    assert trace["version"] == "qnu.catalog-scope/v2"
    _, unknown, _ = resolve("Hải dương học năm 2099", MetadataFilter(), corpus)
    assert unknown[0].data_year == 2099  # Caller applies this even when it matches no units.


@pytest.mark.parametrize("query", ["Hải dương học năm 2031", "Hải dương học"])
def test_missing_intake_or_year_role_requires_clarification(query):
    corpus = [scoped(issued_year=2030), scoped(intake="Đợt B", issued_year=2030)]
    with pytest.raises(AppException) as exc:
        resolve(query, MetadataFilter(), corpus)
    assert exc.value.code == "answer_scope_clarification_required"


def test_exact_role_does_not_change_other_year_and_numeric_count_is_not_year():
    corpus = [scoped(issued_year=2030)]
    _, filters, _ = resolve("Hải dương học năm ban hành 2030", MetadataFilter(), corpus)
    assert filters == [MetadataFilter(program="Hải dương học", issued_year=2030)]
    _, filters, _ = resolve("Hải dương học có 2030 người", MetadataFilter(), corpus)
    assert filters[0].data_year is None and filters[0].issued_year is None


def test_fixed_scope_cannot_be_overridden_or_silently_widened():
    with pytest.raises(AppException) as exc:
        resolve("năm dữ liệu 2032", MetadataFilter(data_year=2031), [scoped()])
    assert exc.value.code == "answer_scope_conflict"


def test_multi_year_query_preserves_disjunction_and_does_not_invent_pairs():
    _, filters, _ = resolve(
        "So sánh năm 2031 và năm 2032", MetadataFilter(), [scoped(), scoped(year=2032)]
    )
    assert {f.data_year for f in filters} == {2031, 2032}
    _, filters, _ = resolve(
        "So sánh năm 2031 và 2032", MetadataFilter(), [scoped(), scoped(year=2032)]
    )
    assert {f.data_year for f in filters} == {2031, 2032}
    with pytest.raises(AppException):
        resolve(
            "So sánh Hải dương học năm 2031 và Khí tượng học năm 2032",
            MetadataFilter(),
            [scoped(), scoped(program="Khí tượng học", year=2032)],
        )


def test_longest_exact_label_does_not_broaden_program_scope():
    corpus = [scoped(program="Điện"), scoped(program="Điện tự động")]
    _, filters, _ = resolve("Điện tự động năm 2031", MetadataFilter(), corpus)
    assert [f.program for f in filters] == ["Điện tự động"]
    _, filters, _ = resolve("So sánh Điện và Điện tự động năm 2031", MetadataFilter(), corpus)
    assert {f.program for f in filters} == {"Điện", "Điện tự động"}


def test_glossary_mined_only_from_explicit_cited_definition_and_stays_out_of_answer_body():
    content, docs = fixture()
    content["source_tables"] = []
    docs[0]["pages"][0]["blocks"].append(
        {"evidence_id": "ev-text", "text": "Ngành Hải dương học (HDH)."}
    )
    content["sections"][0]["paragraphs"][0]["text"] = "HDH có quy chế riêng."
    original = build_chunks(content, docs, 4000)
    enriched = enrich(original, content, docs, 8000)[0]
    definitions = glossary(content, docs)
    assert definitions[0]["expansion"] == "Hải dương học"
    assert definitions[0]["quote"] in docs[0]["pages"][0]["blocks"][-1]["text"]
    assert original_text(enriched) == original[0].text
    hit = SimpleNamespace(
        **{k: getattr(enriched, k) for k in ("kind", "text", "structure")},
        document_id="d",
        version_id="v",
        publication_decision_id="p",
    )
    prompt = evidence_item(hit, "E1")
    assert prompt["id"] == "E1"
    assert prompt["text"] == original[0].text
    assert "structure" not in prompt
    changed = copy.deepcopy(enriched.structure)
    changed["search_context"]["original_text"] = "invented"
    with pytest.raises(AppException):
        original_text(SimpleNamespace(text=enriched.text, structure=changed))


def test_aliases_are_dynamic_scoped_and_ambiguous_definitions_are_not_merged():
    corpus = [scoped(), scoped(program="Khí tượng học", year=2032)]
    for s, expansion in zip(corpus, ("Hải dương học", "Hệ động học"), strict=True):
        s["search_context"] = {"glossary": [{"alias": "HDH", "expansion": expansion}]}
    with pytest.raises(AppException):
        resolve("HDH là gì?", MetadataFilter(), corpus)
    query, filters, _ = resolve("HDH năm 2031", MetadataFilter(), corpus)
    assert "Hải dương học" in query and filters[0].data_year == 2031
    assert filters[0].program == "Hải dương học"


def test_neighbor_scopes_keep_all_question_facets_separate_from_fixed_boundary():
    result = SimpleNamespace(
        trace={
            "facets": [
                {"scope_resolution": {"filters": [{"data_year": 2031}]}},
                {"scope_resolution": {"filters": [{"data_year": 2032}]}},
            ]
        }
    )
    assert {f.data_year for f in result_scopes(result, MetadataFilter())} == {2031, 2032}
